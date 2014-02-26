import ldap, sys, webnotes
from webnotes.model.doc import Document
from webnotes.utils import nowdate,  nowtime
from webnotes.utils.email_lib import sendmail
from webnotes.utils import cstr

def check_profiles_hourly():
	check_profiles_if("Hourly")

def check_profiles_daily():
	check_profiles_if("Daily")

def check_profiles_weekly():
	check_profiles_if("Weekly")

def check_profiles_monthly():
	check_profiles_if("Monthly")

def check_profiles_if(freq):
	if webnotes.conn.get_value("LDAP Settings", None, "profile_check")==freq:
		ldap_connect()

def ldap_connect():
	from webnotes import get_details, set_ldap_connection
	server_details = get_details()

	connect, user_dn, base_dn = set_ldap_connection()
	filters =  "uid=*"

	new_created = [] 
	enabled_profiles = []

	try:
		#if authentication successful, get the full user data	
		connect.simple_bind_s(user_dn, server_details.get('pwd'))

	except ldap.LDAPError, e:
		connect.unbind_s()

	#search for profiels
	result = connect.search_s(base_dn,ldap.SCOPE_SUBTREE,filters)
	
	for dn, r in result:
		exist = profile_check(r.get('mail'))

		if r.get('mail'):	
			enabled_profiles.append(r.get('mail')[0])

		if not exist and r.get('mail'):
			create_profile(r.get('mail')[0], r.get('uid')[0])
			if r.get('mail'):
				new_created.append(r.get('uid')[0])

	disable_profiles(enabled_profiles)
	admin_notification(new_created)

def profile_check(usr):
	if usr:
		return webnotes.conn.sql("select true from tabProfile where name =  %s",str(usr[0]))

def create_profile(usr, name):
	d = Document("Profile")
	d.owner = "Administrator"
	d.email = usr
	d.first_name = name
	d.enabled = 1
	d.creation = nowdate() + ' ' + nowtime()
	d.user_type = "System User"
	d.save(1)

def disable_profiles(enabled_profiles):
	profiels = []
	for pro in enabled_profiles:
		profiels.append("'"+pro+"'")
	profile = webnotes.conn.sql("select name from tabProfile where email not in ("+str(','.join(profiels))+")",as_list=1,debug=1)
	
	for pro in profile:
		webnotes.conn.sql("update tabProfile set enabled = 0 where name = '%s' and name not in ('Administrator','Guest')"%pro[0],debug=1)

def admin_notification(new_profiels):
	msg = get_message(new_profiels)
	receiver = webnotes.conn.get_value('Profile', 'Administrator', 'email')
	subj = "Newly Created profiels"

	sendmail('saurabh.p@indictranstech.com', subject=subj, msg = cstr(msg))

def get_message(new_profiels):

	return """ Hello. New profiles has been created. Please assign roles to them. List is as follws:\n %s """%'\n'.join(new_profiels)


