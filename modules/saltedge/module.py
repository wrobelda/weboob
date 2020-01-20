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


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object

from .browser import SaltEdgeBrowser

__all__ = ['SaltEdgeModule']


class SaltEdgeModule(Module, CapBank):
    NAME = 'saltedge'
    DESCRIPTION = u'Salt Edge Spectre API'
    MAINTAINER = u'Dawid Wróbel'
    EMAIL = 'me@dawidwrobel.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(
        ValueBackendPassword('app_id', label='Application ID', masked=False, required=True),
        ValueBackendPassword('secret', label='Secret Key', masked=True, required=True),
        ValueBackendPassword('customer_id', label='Customer ID', masked=False, required=True))

    BROWSER = SaltEdgeBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['app_id'].get(), self.config['secret'].get(),
                                   self.config['customer_id'].get())

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        return self.browser.iter_coming(account)
