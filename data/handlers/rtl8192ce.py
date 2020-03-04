# (c) 2013 Erick Birbe <erickcion@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from jockey.handlers import ModaliasOverrideHandler


class Module_rtl8192ce_Handler(ModaliasOverrideHandler):

    def __init__(self, ui):

        ModaliasOverrideHandler.__init__(
            self,
            ui,
            package = 'firmware-realtek',
            kernel_module = 'rtl8192ce',
            testfile = '/lib/firmware/rtlwifi/rtl8192cfw.bin',
        )

