#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Glynn Lane
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Better Jamf Printer Policy
    Allows much more flexibility in printer installations.
"""

import os
import re
import sys
import argparse
import subprocess
from SystemConfiguration import SCDynamicStoreCopyConsoleUser


# Paths to binaries
JAMF = ("/usr/local/bin/jamf")
JAMFHELPER = ("/Library/Application Support/JAMF/bin/jamfHelper.app/Contents"
              "/MacOS/jamfHelper")
LAUNCHCTL = ("/bin/launchctl")
LPADMIN = ("/usr/sbin/lpadmin")
LPSTAT = ("/usr/bin/lpstat")

# Error message dialog
GUI_WINDOW_TITLE = ("Printer Installation")
GUI_WINDOW_SUBTITLE = ("Mac Support")
GUI_E_HEADING = ("An error occurred.")
GUI_E_ICON = ("/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources"
              "/AlertStopIcon.icns")
GUI_E_MESSAGE = ("A problem occurred processing your request. Please contact "
                 "the Help Desk for assistance.")


def get_console_user(store=None):
    username, uid, gid = (SCDynamicStoreCopyConsoleUser(None, None, None) or
                          [None])
    username = [username, ""][username in [u'loginwindow', None, u'']]
    return (username, uid, gid)


def build_argparser():
    """
    Creates the argument parser
    Command syntax should look like the following:
    add_remove_printer_by_parameter.py 1 2 3 Add 'Name' 'Opts' 'URI' 'Path' 
        'Description' 'Jamf Event' 'Overwrite'
    """
    description = "Adds or removes printers by parameter."
    parser = argparse.ArgumentParser(description=description)

    # Collect parameters 1-3 into a list; we'll ignore them
    parser.add_argument("params", nargs=3)

    # Assign names to other passed parameters
    parser.add_argument("mode", choices=['Add', 'Remove'],
                        help="Add or Remove printer.")
    parser.add_argument("printer_name", help="Name of printer queue.")
    parser.add_argument("printer_opts_csv", nargs="?",
                        help="""Printer options csv.
                        Use the following syntax:
                        PrinterOption=Value,PrinterOption2=Value""")
    parser.add_argument("printer_uri", nargs="?",
                        help="""URI for Printer.
                        This is how you define where a network printer is.
                        Examples:
                        lpd://10.x.x.x/PrinterQueue for LinePrinterDaemon
                        usb://HP/LazerJet4?serial=42 for USB
                        Use lpstat -s to get printer URIs after mapping.""")
    parser.add_argument("ppd_path", nargs="?",
                        help="""Path to PPD for printer.
                        If this does not exist, then the trigger below will
                        add it to the system.""")
    parser.add_argument("printer_description", nargs="?", default=None,
                        help="""Optional: Printer Description. This is the
                        "Friendly" name of the printer in the GUI. So
                        printer_x5994 becomes "Lobby Printer" in diags. """)
    parser.add_argument("jamf_event", nargs="?",
                        help="""Jamf event (trigger) to install the
                        PPD for this particular printer.""")
    parser.add_argument("overwrite_ppd", nargs="?", default="overwrite",
                        help="""Optional: Should we overwrite the PPD?
                        If nothing is set, we overwrite.""")
    return parser.parse_known_args()[0]


def remove_printer(remove_printer_name):
    """Removes printer using lpadmin. 
    Args:
        (str) remove_printer_name: name of printer to remove.
    Returns:
        (str) success: True or False removal succeeded.
    """
    success = True
    cmd = [LPADMIN, '-x', remove_printer_name]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if err:
            sys.stdout.write("The following error occurred: " + err + ".\n")
            sys.stdout.write("See the next lines for command output:\n")
            sys.stdout.write(out + "\n")
            success = False
    except:
        # Catch possible CalledProcessError and OSError
        sys.stdout.write("Error while running lpstat.")
        success = False

    return success


def return_installed_printer_names():
    """Returns a list of all installed printers using lpstat.
    Args:
        None
    Returns:
        (list) installed_printers: List of all installed printers.
    """
    success = True
    cmd = [LPSTAT, '-s']
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if err:
            sys.stdout.write("The following error occurred: " + err + ".\n")
            sys.stdout.write("See the next lines for command output:\n")
            sys.stdout.write(out + "\n")
            success = False
    except:
        # Catch possible CalledProcessError and OSError
        sys.stdout.write("Error while running lpstat.")
        success = False

    # Process each line looking for whatever is between "device for " and ": "
    # Bound method outside of the list comprehension optimization
    src = re.search
    pattern = r'device for (.*): '
    # This uses nested list comprehension.
    installed_printers = [match.group(1) for line in out.splitlines()
                          for match in [src(pattern, line)] if match]

    return (success, installed_printers)


def display_error(jamfhelper_uid, error_message=GUI_E_MESSAGE):
    """Displays an error if a problem occurs
    Args:
        (int) jamfhelper_uid: UID of ConsoleUser. Needed for displaying
                              windows in user context (launchctl asuser).
        (str) error_message (optional): Message to display in GUI window.
    Returns:
        None"""

    try:
        subprocess.check_output([LAUNCHCTL, 'asuser', str(jamfhelper_uid),
                                JAMFHELPER, '-windowType', 'utility',
                                '-title', GUI_WINDOW_TITLE,
                                '-heading', GUI_E_HEADING,
                                '-icon', GUI_E_ICON,
                                '-description', error_message,
                                '-button1', "Close",
                                '-timeout', "60", '-lockHUD'])
    except subprocess.CalledProcessError as e:
        if str(e.returncode) not in ["2", "3", "239", "243"]:
            sys.stdout.write("The following error occurred: " +
                             str(e.returncode) + ".\n")
            sys.stdout.write("jamfHelper invalid returncodes are:\n" +
                             "  1 - The Jamf Helper was unable to launch\n" +
                             "250 - Bad -windowType\n" +
                             "255 - No -windowType\n")


def call_jamf_policy(path, event):
    """Calls jamf policy to install PPD.
    Args:
        (str) path: expected path of installed PPD.
        (str) event: jamf binary event (jamf policy -event custom_event)
    """
    success = True
    cmd = [JAMF, 'policy', '-event', event]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if err:
            sys.stdout.write("The following error occurred: " + err + ".\n")
            sys.stdout.write("See the next lines for command output:\n")
            sys.stdout.write(out + "\n")
            success = False
        elif 'No policies were found for the' in out:
            sys.stdout.write(out + "\n")
            success = False
    except:
        # Catch possible CalledProcessError and OSError
        sys.stdout.write("Error while running lpadmin.")
        success = False

    # Final check to make sure the policy actually installed the PPD we need.
    if not os.path.exists(path):
        sys.stdout.write("PPD is still not found at " + path + "\n" +
                         "Please check the jamf event name.\n")
        success = False

    return success


def install_printer(name, opts, uri, path, description):
    """Installs printer with lpadmin.
    Args:
        (str) name: name of installed printer
        (list) opts: list of printer options.
        (str) uri: URI of printer object
        (str) path: expected path of installed PPD.
        (str) description: Optional descripton (friendly name) of printer.
    """
    success = True
    cmd = [LPADMIN, '-p', name,
           '-o', ' -o '.join(opts),
           '-E', '-v', uri,
           '-P', path,
           '-D', description]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if err:
            sys.stdout.write("The following error occurred: " + err + ".\n")
            sys.stdout.write("See the next lines for command output:\n")
            sys.stdout.write(out + "\n")
            success = False
    except:
        # Catch possible CalledProcessError and OSError
        sys.stdout.write("Error trying to use lpadmin. Is the path right?")
        success = False

    return success


def main():
    """Main program"""
    # Build the argparser
    args = build_argparser()

    console_user, console_user_uid, console_user_gid = get_console_user()

    # If the script is passed a "Remove" in its arguements, remove the printer.
    if args.mode == "Remove":

        # Get a list of all installed printers.
        return_success, printers = return_installed_printer_names()
        # Fail states should only occur in the case of a fatal error.
        if return_success:
            # If the printer name passed in the parameters is installed:
            if args.printer_name in printers:
                # If the printer was actually removed.
                if remove_printer(args.printer_name):
                    message = ("The printer \"" +
                               args.printer_name +
                               "\" has been removed.")
                    sys.stdout.write(message + "\n")
                    sys.exit(0)
                # It should be unlikely we'd ever get here, but better safe...
                else:
                    message = ("The printer \"" + args.printer_name + "\" " +
                               "was not removed.\n\nPlease contact the " +
                               "Help Desk for further assistance.")
                    sys.stdout.write(message + "\n")
                    display_error(console_user_uid, message)
                    sys.exit(1)
            # If the printer name passed in the parameters is not installed:
            else:
                message = ("The printer \"" + args.printer_name + "\" is " +
                           "not installed.\n\nPlease select an " +
                           "installed printer for removal.")
                sys.stdout.write(message + "\n")
                display_error(console_user_uid, message)
                sys.exit(1)
        # If fatal error like if Apple removed some needed binaries.
        else:
            message = ("An error occurred getting a list of installed " +
                       "printers.\n\nPlease contact the Help Desk" +
                       "for further assistance.")
            sys.stdout.write(message + "\n")
            display_error(console_user_uid, message)
            sys.exit(1)

    # If we're adding a printer.
    if args.mode == "Add":
        # Check to see if the other, non-optional parameters were passed
        # We could not make these "required" in the argparser above because
        # they are not needed when removing printers, but they are when adding.
        if (args.printer_uri == "" and
           str(args.ppd_path) == "" and
           args.jamf_event == ""):
            message = ("Error: An insufficient number of paramaters were " +
                       "supplied to this script.\n\nThis process REQUIRES " +
                       "the URI, PPD path, and jamf event when adding " +
                       "printers.")
            sys.stdout.write(message + "\n")
            display_error(console_user_uid, message)
            sys.exit(1)

        # Take the printer_opts_csv string, which is a csv of printer options,
        # and splice the string into a list. Printers are never shared.
        if args.printer_opts_csv == "":
            printer_options = 'printer-is-shared=False'
        else:
            printer_options = args.printer_opts_csv.split(",")
            printer_options.append('printer-is-shared=False')

        # Get printer model name from the PPD path.
        printer_model = os.path.basename(os.path.splitext(args.ppd_path)[0])
        # Overwrite PPD if requested, or install if not in place.
        if (not os.path.exists(args.ppd_path) or
           args.overwrite_ppd.lower() == 'overwrite'.lower()):
            sys.stdout.write("PostScript Printer Definition (PPD) needs " +
                  "installation.\n Triggering jamf policy by event: " +
                  args.jamf_event + ".\n")
            if not call_jamf_policy(args.ppd_path, args.jamf_event):
                message = ("The printer driver for the \"" + printer_model +
                           "\" was not installed.\n\nPlease contact the " +
                           "Help Desk for further assistance.")
                sys.stdout.write(message + "\n")
                display_error(console_user_uid, message)
                sys.exit(1)

        """Install the printer.
        Printer options are joined by " -o ". This means that the options are
        passed to lpadmin separated with the correct switch. By default, the
        only option is that the printer is not shared. Any additional options
        can be handled with ease.
        """
        if install_printer(args.printer_name, printer_options,
                           args.printer_uri, args.ppd_path,
                           args.printer_description):
            message = ("The \"" + printer_model + "\" printer named \"" +
                       args.printer_name + "\" was installed successfully.")
            sys.stdout.write(message + "\n")
            sys.exit(0)
        else:
            message = ("The \"" + printer_model + "\" printer named \"" +
                       args.printer_name + "\" was not installed.\n\n" +
                       "Please contact the Help Desk for " +
                       "further assistance.")
            sys.stdout.write(message + "\n")
            display_error(console_user_uid, message)
            sys.exit(1)


if __name__ == '__main__':
    main()
