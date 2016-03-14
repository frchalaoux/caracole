#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime

from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
import django.contrib.auth.views as auth_view
from django.http import HttpResponseForbidden, HttpResponseBadRequest

from .. import models as m
from .edit_subgroup_purchases import edit_subgroup_purchases
from .edit_user_purchases import edit_user_purchases
from .user_registration import user_register, user_register_post
from .edit_delivery_products import edit_delivery_products
from .edit_user_memberships import edit_user_memberships, json_memberships
from .adjust_subgroup import adjust_subgroup
from .view_purchases import \
    view_purchases_html, view_purchases_pdf, view_purchases_latex, view_purchases_xlsx, view_cards_latex


def get_network(x):
    return m.Network.objects.get(id=int(x))


def get_subgroup(x):
    return m.Subgroup.objects.get(id=int(x))


def get_delivery(x):
    return m.Delivery.objects.get(id=int(x))


def get_candidacy(x):
    return m.Candidacy.objects.get(id=int(x))


def active_deliveries(request):
    """Main page: list deliveries open for ordering as a user, networks for which the user is full admin,
     and orders for which he has subgroup-admin actions to take."""

    user = request.user
    if not user.is_authenticated(): return redirect(reverse(auth_view.login))

    SUBGROUP_ADMIN_STATES = [m.Delivery.ORDERING_ALL, m.Delivery.ORDERING_ADMIN,m.Delivery.REGULATING]

    vars = {'user': request.user, 'Delivery': m.Delivery, 'SubgroupState': m.SubgroupStateForDelivery}
    user_subgroups = m.Subgroup.objects.filter(users__in=[user])
    user_networks = [sg.network for sg in user_subgroups]
    vars['deliveries'] = m.Delivery.objects.filter(network__in=user_networks, state=m.Delivery.ORDERING_ALL)

    vars['network_admin'] = m.Network.objects.filter(staff__in=[user])
    subgroup_admin = m.Subgroup.objects.filter(staff__in=[user])
    subgroup_admin = [{'sg': sg,
                       'dv': sg.network.delivery_set.filter(state__in=SUBGROUP_ADMIN_STATES),
                       'cd': sg.candidacy_set.all()}
                       for sg in subgroup_admin]
    subgroup_admin = [sg_dv_cd for sg_dv_cd in subgroup_admin if sg_dv_cd['dv'].exists() or sg_dv_cd['cd'].exists]
    vars['subgroup_admin'] = subgroup_admin
    return render_to_response('active_deliveries.html', vars)


def candidacy(request):
    """Generate a page to choose and request candidacy among the legal ones."""
    user = request.user
    user_of_subgroups = m.Subgroup.objects.filter(users__in=[user])
    candidate_to_subgroups = m.Subgroup.objects.filter(candidacy__user__in=[user])
    # name, user_of, candidate_to, can_be_candidate_to
    networks = []
    for nw in m.Network.objects.all():
        us = user_of_subgroups.filter(network=nw)
        cs = candidate_to_subgroups.filter(network=nw)
        item = {'name': nw.name,
                'user_of': us[0] if us.exists() else None,
                'candidate_to': cs[0] if cs.exists() else None,
                'can_be_candidate_to': nw.subgroup_set.all()}

        for non_candidate in (item['user_of'], item['candidate_to']):
            if non_candidate:
                item['can_be_candidate_to'] = item['can_be_candidate_to'].exclude(id=non_candidate.id)
        networks.append(item)
    return render_to_response('candidacy.html', {'networks': networks})



def apply_candidacy(request, subgroup):
    """Create the candidacy, after checking again its legality."""
    user = request.user
    sg = get_subgroup(subgroup)


def validate_candidacy(request, candidacy, response):
    """A (legal) candidacy has been answered by an admin.
    Check the admin was entitled to accept it, and perform corresponding membership changes."""
    # Response = 'Y':
    # If cd.user was in a subgroup of that nw, cancel it + subgroup admin status if applicable.
    # Exception: if he's nw-admin + sg-admin, transfer sg-admin status.
    # Delete candidacy and create user membership instead.
    # Send e-mail confirmation.
    #
    # Response = 'N': cancel candidacy, send an e-mail to candidate with rejecting admin's contact.
    user = request.user
    cd = get_candidacy(candidacy)


def network_admin(request, network):
    user = request.user
    nw = get_network(network)
    vars = {'user': user, 'nw': nw, 'deliveries': m.Delivery.objects.filter(network=nw)}
    return render_to_response('network_admin.html', vars)


def edit_delivery(request, delivery):
    """Edit a delivery as a full network admin: act upon its lifecycle, control which subgroups have been validated,
    change the products characteristics, change other users' orders."""
    dv = m.Delivery.objects.get(id=delivery)
    if dv.network.staff.filter(id=request.user.id).exists():
        # All subgroups in the network for network admins
        subgroups = dv.network.subgroup_set.all()
    else:
        # Only subgroups in which user in subgroup-admin
        subgroups = dv.network.subgroup_set.filter(staff=request.user)
    vars = {
        'user': request.user,
        'dv': dv,
        'subgroups': subgroups,
        'Delivery': m.Delivery,
        'SubgroupState': m.SubgroupStateForDelivery,
        'steps': [{'s': s, 'text': m.Delivery.STATE_CHOICES[s], 'is_done': dv.state>=s, 'is_current': dv.state==s} for s in 'ABCDEF'],
        'CAN_EDIT_PURCHASES': dv.state in [m.Delivery.ORDERING_ALL, m.Delivery.ORDERING_ADMIN, m.Delivery.REGULATING],
        'CAN_EDIT_PRODUCTS': dv.state != m.Delivery.TERMINATED
    }
    return render_to_response('edit_delivery.html', vars)


def create_delivery(request, network):
    """Create a new delivery, then redirect to its edition page."""
    network = m.Network.objects.get(id=network)
    if request.user not in network.staff.all():
        return HttpResponseForbidden('Réservé aux administrateurs du réseau '+network.name)
    months = [u'Janvier', u'Février', u'Mars', u'Avril', u'Mai', u'Juin', u'Juillet',
              u'Août', u'Septembre', u'Octobre', u'Novembre', u'Décembre']
    now = datetime.now()
    name = '%s %d' % (months[now.month-1], now.year)
    n = 1
    while m.Delivery.objects.filter(network=network, name=name).exists():
        if n == 1:
            fmt = u"%dème de " + name
        n += 1
        name = fmt % n
    d = m.Delivery.objects.create(network=network, name=name, state=m.Delivery.PREPARATION)
    d.save()
    return redirect('edit_delivery_products', delivery=d.id)


def set_delivery_state(request, delivery, state):
    """Change a delivery's state."""
    dv = get_delivery(delivery)
    if request.user not in dv.network.staff.all():
        return HttpResponseForbidden('Réservé aux administrateurs du réseau '+dv.network.name)
    if state not in m.Delivery.STATE_CHOICES:
        return HttpResponseBadRequest(state+" n'est pas un état valide.")
    dv.state = state
    dv.save()
    return redirect('edit_delivery', delivery=dv.id)


def set_subgroup_state_for_delivery(request, subgroup, delivery, state):
    """Change the state of a subgroup/delivery combo."""
    dv = get_delivery(delivery)
    sg = get_subgroup(subgroup)
    dv.set_stateForSubgroup(sg, state)
    target = request.REQUEST.get('next', False)
    if target:
        return redirect(target)
    else:
        return redirect('edit_delivery', delivery=dv.id)


def view_emails(request, network=None, subgroup=None):
    # TODO: protect from unwarranted access
    vars = {'user': request.user}
    if network:
        vars['network'] = m.Network.objects.get(id=int(network))
    if subgroup:
        sg = m.Subgroup.objects.get(id=subgroup)
        vars['subgroups'] = [sg]
        if not network:
            vars['network'] = sg.network
    elif network:
        vars['subgroups'] = m.Subgroup.objects.filter(network_id=network)
    else:
        raise Exception("Need network or subgroup")
    return render_to_response('emails.html', vars)


def view_history(request):
    orders = [(nw, m.Order(request.user, dv))
              for nw in m.Network.objects.all()
              for dv in nw.delivery_set.all()]
    orders = [(nw, od) for (nw, od) in orders if od.price > 0]  # Filter out empty orders
    vars = {'user': request.user, 'orders': orders}
    return render_to_response("view_history.html", vars)
