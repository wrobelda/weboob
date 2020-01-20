# -*- coding: utf-8 -*-

# Copyright(C) 2020      Dawid Wróbel
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals

from functools import wraps
import json

from weboob.browser.browsers import APIBrowser
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import NotAvailable

ACCOUNT_TYPES = {
    'account': Account.TYPE_CHECKING,
    'bonus': Account.TYPE_UNKNOWN,
    'card': Account.TYPE_CARD,
    'checking': Account.TYPE_CHECKING,
    'credit': Account.TYPE_CONSUMER_CREDIT,
    'credit_card': Account.TYPE_CARD,
    'debit_card': Account.TYPE_CARD,
    'ewallet': Account.TYPE_CHECKING,
    'insurance': Account.TYPE_LIFE_INSURANCE,
    'investment': Account.TYPE_MARKET,
    'loan': Account.TYPE_LOAN,
    'mortgage': Account.TYPE_MORTGAGE,
    'savings': Account.TYPE_SAVINGS
}

def need_connections(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.connections:
            self.get_connections()
        return func(self, *args, **kwargs)

    return wrapper


class SaltEdgeBrowser(APIBrowser):
    BASEURL = 'https://www.saltedge.com'
    VERIFY = True

    def __init__(self, app_id, secret, customer_id, *args, **kwargs):
        super(SaltEdgeBrowser, self).__init__(*args, **kwargs)
        self.app_id = app_id
        self.secret = secret
        self.customer_id = customer_id
        self.connections = []
        self.request_headers = {}

    def build_request(self, *args, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['App-id'] = self.app_id
        kwargs['headers']['Secret'] = self.secret

        return super(APIBrowser, self).build_request(*args, **kwargs)

    # TODO: handle pagination using Pages
    def get_connections(self, from_id=0):
        self.open('api/v5/connections?customer_id=%s&from_id=%i' % (self.customer_id, from_id))
        response = self.request('api/v5/connections?customer_id=%s&from_id=%i' % (self.customer_id, from_id),
                                headers=self.request_headers)
        self.connections.extend(response['data'])

        if response['meta'].get('next_id'):
            self.get_connections(self, response['meta']['next_id'])

    # TODO: handle pagination using Pages
    def get_connection_accounts(self, connection, from_id=0):
        self.open('api/v5/accounts?connection_id=%s&from_id=%i' % (connection['id'], from_id))
        response = self.request('api/v5/accounts?connection_id=%s&from_id=%i' % (connection['id'], from_id),
                                headers=self.request_headers)
        accounts = response['data']

        for account in accounts:
            a = Account()
            a.bank_name = connection['provider_name']
            a.type = ACCOUNT_TYPES.get(account['nature'], Account.TYPE_UNKNOWN)
            a.label = account['name']
            a.id = account['id']
            a.number = NotAvailable
            a.iban = account['extra'].get('iban', NotAvailable)
            a.balance = CleanDecimal().filter(account['balance'])
            a.currency = account['currency_code']

            a._connection_id = connection['id']
            yield a

        if response['meta'].get('next_id'):
            yield from self.get_connection_accounts(connection, response['meta']['next_id'])

    @need_connections
    def iter_accounts(self):
        for connection in self.connections:
            yield from self.get_connection_accounts(connection)

    # TODO: handle pagination using Pages
    # TODO: use time and posting_time if present
    # TODO: handle pending transactions
    # TODO: handle the transaction type
    @need_connections
    def iter_history(self, account, from_if=0):
        self.open('api/v5/transactions?connection_id=%s&account_id=%s' % (account._connection_id, account.id))
        response = self.request('api/v5/transactions?connection_id=%s&account_id=%s' % (account._connection_id,
                                                                                        account.id),
                                headers=self.request_headers)

        transactions = response['data']

        for transaction in transactions:
            t = Transaction()

            if transaction['status'] is 'pending':
                continue

            t.date = Date().filter(transaction['made_on'])
            t.id = transaction['id']
            t.amount = CleanDecimal().filter(transaction['amount'])
            t.raw = transaction['description']
            t.category = transaction['category']

            if 'additional' in transaction['extra']:
                t.raw += '\n' + transaction['extra']['additional']

            if 'payee' in transaction['extra']:
                t.label = transaction['extra']['payee']

            if 'posting_date' in transaction['extra']:
                t.rdate = Date().filter(transaction['extra']['posting_date'])

            if 'original_currency_code' in transaction['extra']:
                t.original_currency = transaction['extra']['original_currency_code']

            if 'original_amount' in transaction['extra']:
                t.original_amount = CleanDecimal().filter(transaction['extra']['original_amount'])

            yield t

        if response['meta'].get('next_id'):
            yield self.iter_history(account, response['meta']['next_id'])
