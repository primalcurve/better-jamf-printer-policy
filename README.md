# better-jamf-printer-policy
A better way for Jamf Pro Admins to add and remove printers.

Many thanks to [haircut](https://github.com/haircut "Haircut's Github") for the inspiration for this from his excellent repo [better-jamf-policy-deferral](https://github.com/haircut/better-jamf-policy-deferral "better-jamf-policy-deferral GitHub repo").

## Why a different process?
For whatever reason, Jamf has never made it easy for us to edit existing printer definitions. There is no current way through the web interface or API to modify the printer definitions. The only way to tinker with them *in situ* is to crack open the DB and start modifying tables. This is not even an option for cloud-hosted Jamf Pro environments.

Even adding printers is a pain. We have had to capture them with Jamf Admin for years. It's a terrible process. You have to install the printer, then hope that the printer definition doesn't already exist in Jamf Admin otherwise you spend a half hour pulling out your hair because you cannot figure out why it cannot "see" the new printer, until you remember, years ago in your CCT, that it will not show printers it thinks it knows.

It's clunky, slow, and not even remotely modular. It needs to go.

## What's the difference?
This process uses a Python script to modify printers, and this will empower you with the ability to modify existing printers with a couple of mouse clicks without needing to spend several hours working on one printer just because it has a new IP. Now you change one field in the printer policy and you're done.

Will it be a bit more hands-on than the old method? At first, *yes*, but you will be rewarded with a greater understanding of how printer definitions work as well as a setup that is highly modular and can be brought to bear on multiple printers in quick succession. Wouldn't it be nice to be able to setup two identical printers by simply cloning the policy of the other printer and changing the IP? That's something you'll be able to do!

## In Practice
Installation (and removal) of Printers is now handled by better_jamf_printer_policy.py

### What does the script do under the hood?
The script just installs the PPDs, then runs the following command on the endpoint:

```bash
$ lpadmin -p <printer_name> -o printer-option="Value" -E -v uri://printer_address/queue_name -P '/Library/Printers/PPDs/Contents/Resources/Some Printer Model 5000.gz' -D "Printer Description"
```

### How do I use it?

Simply create a new policy, add the script, and then fill out the parameters. If you need help getting the pieces, check out the Docs.

There are a couple of things you will need besides the printer installation policy, but please see the Docs for information on that.
