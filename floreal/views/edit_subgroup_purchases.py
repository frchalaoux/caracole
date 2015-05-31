#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
from django.shortcuts import redirect, render_to_response
from django.core.context_processors import csrf
from django.http import HttpResponseForbidden

from .. import models as m
from ..penury import set_limit
from .delivery_description import delivery_description
from .view_purchases import get_subgroup

def edit_subgroup_purchases(request, delivery):
    """Allows to change the purchases of user's subgroup. Subgroup staff only."""
    delivery = m.Delivery.objects.get(id=delivery)
    user = request.user
    subgroup = get_subgroup(request, delivery.network)

    if request.user not in subgroup.staff.all() and request.user not in delivery.network.staff.all():
        return HttpResponseForbidden('Réservé aux administrateurs du réseau ' + delivery.network.name + \
                                     ' ou du sous-groupe '+subgroup.name)

    if request.method == 'POST':
        _parse_form(request)
        return redirect("edit_subgroup_purchases", delivery=delivery.id)
    else:
        vars = delivery_description(delivery, [subgroup], user=user)
        vars.update(csrf(request))
        return render_to_response('edit_subgroup_purchases.html', vars)


def _parse_form(request):
    """
    Parse responses from subgroup purchase editions.
    :param request:
    :return:
    """

    d = request.POST
    for pd, u in re.findall(r'pd(\d+)u(\d+)', d['modified']):
        ordered = float(d['pd%su%s' % (pd, u)])
        try:
            pc = m.Purchase.objects.get(product_id=pd, user_id=u)
            if ordered != 0:
                print "Updating purchase %d" % pc.id
                pc.ordered = ordered
                pc.granted = ordered
                pc.save(force_update=True)
            else:
                print "Cancelling purchase %d" % pc.id
                pc.delete()
        except m.Purchase.DoesNotExist:
            if ordered != 0:
                print "Creating purchase for pd=%s, u=%s, q=%f" % (pd, u, ordered)
                m.Purchase.objects.create(product_id=pd, user_id=u, ordered=ordered, granted=ordered)
        # Update ordered / granted mismatches in case of product penury, for every purchase
        set_limit(pd)

    return True  # true == no error
