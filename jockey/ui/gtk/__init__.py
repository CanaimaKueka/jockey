import sys, os.path, os

from gi.repository import GObject, GLib, GdkPixbuf, Gtk, Notify


import jockey.ui
from jockey.oslib import OSLib

class GtkUI(jockey.ui.AbstractUI):
    '''GTK user interface implementation.'''

    #
    # Implementation of required AbstractUI methods
    # 

    def convert_keybindings(self, str):
        '''
        Keyboard accelerator aware gettext() wrapper.
        
        This optionally converts keyboard accelerators to the appropriate
        format for the frontend.

        A double underscore ('__') is converted to a real '_'.
        '''
        # nothing to do for GTK
        return str

    def ui_init(self):
        '''Initialize UI.'''

        # load UI
        self.widgets = Gtk.Builder()
        ui_path = '/usr/share/jockey/jockey-gtk.ui'
        if not os.path.exists(ui_path):
            ui_path = os.path.join(os.path.dirname(__file__), 'jockey-gtk.ui')
        self.widgets.add_from_file(ui_path)
        self.widgets.connect_signals(self)

        self.switch_ignore_active_signal = self.w('switch_ignore').connect(
            'notify::active',
            self.on_switch_ignore_toggle
        )

        self.w('label_license_label').set_label(self.string_license_label)
        self.w('linkbutton_licensetext').set_label('(%s)' % self.string_details)
        self.w('dialog_licensetext').set_title(self.string_license_dialog_title)

        self.loop = GLib.MainLoop()


    def ui_show_main(self):
        '''Show main window.'''

        self.treeview = self.w('treeview_drivers')

        self.w('dialog_manager').set_title(self.main_window_title())

        # initialize handler treeview (but only do it once)
        if not self.treeview.get_columns():
            self.treeview.set_headers_visible(False)

            # icon
            pixbuf_renderer = Gtk.CellRendererPixbuf()
            col_icon = Gtk.TreeViewColumn()
            col_icon.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            col_icon.set_expand(False)
            col_icon.pack_start(pixbuf_renderer, False)
            col_icon.add_attribute(pixbuf_renderer, 'pixbuf', 1)
            self.treeview.append_column(col_icon)

            # name
            text_renderer = Gtk.CellRendererText()
            col_name = Gtk.TreeViewColumn()

            col_icon.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            col_name.set_expand(True)
            col_name.pack_start(text_renderer, True)
            col_name.add_attribute(text_renderer, 'text', 2)
            self.treeview.append_column(col_name)

        self.treeview.grab_focus()
        self.update_driver_info_ui(None)
        self.update_tree_model()

        # show help button?
        if not OSLib.inst.ui_help_available(self):
            self.w('button_help').hide()
            # EDGE is the default, but that centers if there is just one button
            self.w('button_box_main').set_layout(Gtk.ButtonBoxStyle.END)

        # default height of details scrollwindow is too small
        self.w('dialog_manager').set_default_size(-1, 550)

        # default vpane size
        if len(self.get_displayed_handlers()) < 2:
            self.w('vpaned1').set_position(36)
        elif len(self.get_displayed_handlers()) < 4:
            self.w('vpaned1').set_position(72)
        else:
            self.w('vpaned1').set_position(100)

        # lift the curtain
        self.w('dialog_manager').show()

    def ui_main_loop(self):
        '''Main loop for the user interface.
        
        This should return if the user wants to quit the program, and return
        the exit code.
        '''

        if not self.loop.is_running():
            self.loop.run()
            exit(0)

    def error_message(self, title, text):
        '''Present an error message box.'''

        self.msgbox = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE, message_format=text)
        if title:
            self.msgbox.set_title(title)
        self.msgbox.run()
        self.msgbox.destroy()
        self.msgbox = None

    def confirm_action(self, title, text, subtext=None, action=None):
        '''Present a confirmation dialog.

        If action is given, it is used as button label instead of the default
        'OK'.  Return True if the user confirms, False otherwise.
        '''
        if action:
            self.msgbox = Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION,
                message_format=text)
            self.msgbox.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            self.msgbox.add_button(action, Gtk.ResponseType.OK).set_image(
                Gtk.Image.new_from_stock(Gtk.STOCK_APPLY,
                Gtk.IconSize.BUTTON))
        else:
            self.msgbox = Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION,
                message_format=text, buttons=Gtk.ButtonsType.OK_CANCEL)
        if subtext:
            self.msgbox.format_secondary_text(subtext)
        if title:
            self.msgbox.set_title(title)
        ret = self.msgbox.run()
        self.msgbox.destroy()
        self.msgbox = None
        return ret == Gtk.ResponseType.OK

    def ui_notification(self, title, text, show_button=True):
        '''
        Present a notification popup with a button to show the UI.
        '''
        self.show_notification(
            title,
            text=text,
            icon='jockey',
            actions={
                'show_jockey': {
                    'label': self.string_show,
                    'callback': lambda x, y, z: self.ui_show_main()
                }
            } if show_button else show_button
        )

    def show_notification(self, title, text=None, icon=None, actions=None):
        '''
        Show a notification.
        `actions` is of the form:
        {'action_id': {'label':'Label text', 'callback': callback}}
        '''
        self.ui_idle()

        Notify.init('jockey')

        notification = Notify.Notification.new(title, text, icon)

        if actions:
            for k, v in actions.iteritems():
                notification.add_action(k, v['label'], v['callback'],
                                        None, None)

        notification.set_timeout(10000)
        try:
            notification.show()
        except GLib.GError as e:
            sys.stderr.write('Failed to show notification: %s\n' % str(e))

        self.ui_main_loop()

    def ui_idle(self):
        '''Process pending UI events and return.

        This is called while waiting for external processes such as package
        installers.
        '''
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

    def ui_progress_start(self, title, description, total):
        '''Create a progress dialog.'''

        self.w('progress').set_fraction(0)
        self.w('label_description').set_label(description)
        self.w('window_progress').set_title(title)
        self.w('window_progress').set_transient_for(self.w('dialog_manager'))
        self.w('window_progress').show()
        self.cancel_progress = False

    def ui_progress_update(self, current, total):
        '''Update status of current progress dialog.
        
        current/total specify the number of steps done and total steps to
        do, or -1 if it cannot be determined. In this case the dialog should
        display an indeterminated progress bar (bouncing back and forth).

        This should return True to cancel, and False otherwise.
        '''
        if current < 0 or total < 0:
            self.w('progress').set_pulse_step(0.1)
            self.w('progress').pulse()
        else:
            self.w('progress').set_fraction(float(current)/total)
        return self.cancel_progress

    def ui_progress_finish(self):
        '''Close the current progress dialog.'''

        self.w('window_progress').hide()

    #
    # helper functions
    #

    def w(self, widget):
        '''Shortcut for getting an UI widget from GtkBuilder.'''

        return self.widgets.get_object(widget)

    def update_tree_model(self):
        '''Update treeview to current set of handlers and their states.'''

        # handler ID, icon, name
        self.model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf,
                GObject.TYPE_STRING)

        theme = Gtk.IconTheme.get_default()
        cur_path = self.treeview.get_cursor()[0]

        for h_id in self.get_displayed_handlers():
            info = self.get_ui_driver_info(h_id)
            if info['needs_reboot']:
                pixbuf = theme.load_icon(Gtk.STOCK_REFRESH, 16, 0)
            elif info['enabled']:
                try:
                    pixbuf = theme.load_icon('jockey-enabled', 16, 0)
                except GLib.GError:
                    pixbuf = theme.load_icon(Gtk.STOCK_YES, 16, Gtk.IconLookupFlags.USE_BUILTIN)
            else:
                if info['dummy']:
                    pixbuf = theme.load_icon(
                        Gtk.STOCK_CANCEL,
                        16,
                        Gtk.IconLookupFlags.USE_BUILTIN
                    )
                elif info['ignored']:
                    try:
                        pixbuf = theme.load_icon('jockey-ignored', 16, 0)
                    except GLib.GError:
                        pixbuf = theme.load_icon(
                            Gtk.STOCK_NO,
                            16,
                            Gtk.IconLookupFlags.USE_BUILTIN
                        )
                else:
                    try:
                        pixbuf = theme.load_icon('jockey-disabled', 16, 0)
                    except GLib.GError:
                        pixbuf = theme.load_icon(Gtk.STOCK_NO, 16, Gtk.IconLookupFlags.USE_BUILTIN)

            iter = self.model.append([h_id, pixbuf, info['name'].encode('UTF-8')])
            if not cur_path:
                cur_path = self.model.get_path(iter)

        self.treeview.set_model(self.model)
        if cur_path:
            self.treeview.set_cursor(cur_path, None, False)
        self.treeview.expand_all()

        self.w('label_heading').set_label('<span weight="bold">%s</span>\n\n%s' %
            self.main_window_text())

    def update_driver_info_ui(self, handler_id):
        '''Update UI elements which show the driver details.

        If handler_id is None, then no driver is selected, no information
        shown, and the appropriate controls are disabled.
        '''

        info = self.get_ui_driver_info(handler_id)

        self.w('label_drivername').set_label('<b>%s</b>' % info['name'])
        self.current_driver_name = info['name']
        d = info['description']
        self.w('textview_description').get_buffer().set_text(d, len(d))
        self.w('button_toggle').show()

        iconsize_button = Gtk.IconSize.BUTTON

        if info['certified'] == None:
            self.w('image_certification').hide()
        elif info['certified']:
            self.w('image_certification').show()
            self.w('image_certification').set_from_icon_name('jockey-certified', iconsize_button)
        else:
            self.w('image_certification').show()
            self.w('image_certification').set_from_stock(Gtk.STOCK_DIALOG_WARNING, iconsize_button)
        self.w('label_certification').set_label(info['certification_label'])
        if info['free'] == None:
            self.w('image_license').hide()
            self.w('label_license_label').hide()
        elif info['free']:
            self.w('image_license').show()
            self.w('label_license_label').show()
            self.w('image_license').set_from_icon_name('jockey-free', iconsize_button)
        else:
            self.w('image_license').show()
            self.w('label_license_label').show()
            self.w('image_license').set_from_icon_name('jockey-proprietary',
                iconsize_button)
        self.w('label_license').set_label(info['license_label'])
        if info['license_text']:
            self.w('linkbutton_licensetext').show()
            self.current_license_text = info['license_text']
        else:
            self.w('linkbutton_licensetext').hide()
            self.current_license_text = None

        self.w('label_ignore').set_label(self.string_label_ignore)
        self.w('label_ignore').set_sensitive(False)
        self.w('switch_ignore').set_sensitive(False)
        if info['enabled'] == None:
            self.w('image_enabled').hide()
        elif info['needs_reboot']:
            self.w('button_toggle').hide()
            self.w('image_enabled').show()
            self.w('image_enabled').set_from_stock(Gtk.STOCK_REFRESH, iconsize_button)
        elif info['enabled']:
            self.w('image_enabled').show()
            self.w('image_enabled').set_from_icon_name('jockey-enabled', iconsize_button)
        else:
            self.w('image_enabled').show()
            if info['ignored']:
                self.w('image_enabled').set_from_icon_name('jockey-ignored', iconsize_button)
                self.w('switch_ignore').disconnect(
                    self.switch_ignore_active_signal
                )
                self.w('switch_ignore').set_active(True)
                self.switch_ignore_active_signal = self.w(
                    'switch_ignore'
                ).connect(
                    'notify::active',
                    self.on_switch_ignore_toggle
                )
                self.w('button_toggle').set_image(
                    self._new_image_from_icon_name('jockey-ignored', iconsize_button)
                )
            else:
                self.w('switch_ignore').disconnect(
                    self.switch_ignore_active_signal
                )
                self.w('switch_ignore').set_active(False)
                self.switch_ignore_active_signal = self.w(
                    'switch_ignore'
                ).connect(
                    'notify::active',
                    self.on_switch_ignore_toggle
                )
                self.w('image_enabled').set_from_icon_name('jockey-disabled', iconsize_button)
            self.w('switch_ignore').set_sensitive(True)
            self.w('label_ignore').set_sensitive(True)
        self.w('label_status').set_label(info['status_label'])

        if not info.get('dummy', False):
            if not info['button_toggle_label']:
                self.w('button_toggle').set_label(self.string_button_enable)
                self.w('button_toggle').set_sensitive(False)
            else:
                self.w('button_toggle').set_sensitive(True)
                self.w('button_toggle').set_label(info['button_toggle_label'])
                if info['enabled']:
                    self.w('button_toggle').set_image(
                        self._new_image_from_icon_name('jockey-enabled', iconsize_button)
                    )
                else:
                    if info['ignored']:
                        self.w('switch_ignore').disconnect(
                            self.switch_ignore_active_signal
                        )
                        self.w('switch_ignore').set_active(True)
                        self.switch_ignore_active_signal = self.w(
                            'switch_ignore'
                        ).connect(
                            'notify::active',
                            self.on_switch_ignore_toggle
                        )
                        self.w('button_toggle').set_image(
                            self._new_image_from_icon_name('jockey-ignored', iconsize_button)
                        )
                    else:
                        self.w('switch_ignore').set_active(False)
                        self.w('button_toggle').set_image(
                            self._new_image_from_icon_name('jockey-disabled', iconsize_button)
                        )
        else:
            # The device is not supported

            # Reuse some image and labels
            self.w('image_certification').set_from_stock(
                Gtk.STOCK_CANCEL, iconsize_button
            )
            self.w('label_certification').set_label(
                self.string_unsupported_driver
            )
            self.w('image_enabled').set_from_stock(
                Gtk.STOCK_CANCEL, iconsize_button
            )

            # Hide things that make no sense for unsupported drivers
            self.w('image_license').hide()
            self.w('label_license_label').hide()
            self.w('label_license').hide()
            self.w('button_toggle').set_sensitive(False)

    #
    # event callbacks
    #

    def on_quit(self, *args):
        if self.loop.is_running():
            self.loop.quit()

    def on_button_help_clicked(self, widget):
        OSLib.inst.ui_help(self)
        return True

    def on_switch_ignore_toggle(self, widget, active):
        self.treeview.set_sensitive(False)
        h_id = self.model[self.treeview.get_cursor()[0]][0]
        if self.toggle_handler_ignore(h_id):
            self.update_tree_model()
        self.treeview.set_sensitive(True)
        return True

    def on_button_toggle_clicked(self, widget):
        self.treeview.set_sensitive(False)
        if self.set_handler_enable(self.model[self.treeview.get_cursor()[0]][0],
            'toggle', False):
            self.update_tree_model()
        self.treeview.set_sensitive(True)
        return True

    def on_treeview_drivers_cursor_changed(self, widget):
        path = widget.get_cursor()[0]
        if path:
            h_id = self.model[path][0]
        else:
            h_id = None
        self.update_driver_info_ui(h_id)
        return True

    def on_progress_cancel(self, *args):
        self.cancel_progress = True
        return True

    def on_linkbutton_licensetext_clicked(self, widget):
        self.w('label_license_drivername').set_label('<b>%s</b>' %
            self.current_driver_name)
        self.w('textview_license_text').get_buffer().set_text(self.current_license_text)
        self.w('dialog_licensetext').set_default_size(600, 480)
        self.w('dialog_licensetext').run()
        self.w('dialog_licensetext').hide()
        return True

    def _new_image_from_icon_name(self, icon_name, icon_size):
        try:
            return Gtk.Image.new_from_icon_name(icon_name, icon_size)
        except AttributeError:
            return Gtk.image_new_from_icon_name(icon_name, icon_size)
