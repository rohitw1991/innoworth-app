# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
"""will be called by scheduler"""

import webnotes
from webnotes.utils import scheduler
	
def execute_all():
	"""
		* get support email
		* recurring invoice
	"""
	# pull emails
	from support.doctype.support_ticket.get_support_mails import get_support_mails
	run_fn(get_support_mails)

	from hr.doctype.job_applicant.get_job_applications import get_job_applications
	run_fn(get_job_applications)

	from selling.doctype.lead.get_leads import get_leads
	run_fn(get_leads)

	from webnotes.utils.email_lib.bulk import flush
	run_fn(flush)
	
def execute_daily():
	# event reminders
	from core.doctype.event.event import send_event_digest
	run_fn(send_event_digest)
	
	# email digest
	from setup.doctype.email_digest.email_digest import send
	run_fn(send)

	# run recurring invoices
	from accounts.doctype.sales_invoice.sales_invoice import manage_recurring_invoices
	run_fn(manage_recurring_invoices)

	# send bulk emails
	from webnotes.utils.email_lib.bulk import clear_outbox
	run_fn(clear_outbox)

	# daily backup
	from setup.doctype.backup_manager.backup_manager import take_backups_daily
	run_fn(take_backups_daily)

	# check reorder level
	from stock.utils import reorder_item
	run_fn(reorder_item)
	
	#ldap profile check
	from  controllers.ldap_profile_check import check_profiles_daily
	run_fn(check_profiles_daily)	
		
	# scheduler error
	scheduler.report_errors()

def execute_weekly():
	from setup.doctype.backup_manager.backup_manager import take_backups_weekly
	run_fn(take_backups_weekly)

	#ldap profile check
	from  controllers.ldap_profile_check import check_profiles_weekly
	run_fn(check_profiles_weekly)

def execute_monthly():
	#ldap profile check
	from  controllers.ldap_profile_check import check_profiles_monthly
	run_fn(check_profiles_monthly)

def execute_hourly():
	#ldap profile check
	from  controllers.ldap_profile_check import check_profiles_hourly
	run_fn(check_profiles_hourly)
	
def run_fn(fn):
	try:
		fn()
	except Exception, e:
		scheduler.log(fn.func_name)
