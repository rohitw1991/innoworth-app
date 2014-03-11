# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

class ItemPriceDuplicateItem(webnotes.ValidationError): pass

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl


	def on_update(self):
		pass
		'''
		import urllib.request
                import json     
                
                json_dict = [{"item_code":self.doc.item_code,"ref_rate":self.doc.ref_rate,"buying_or_selling":self.doc.buying_or_selling,"price_list":self.doc.price_list}]
                json_data = json.dumps(json_dict)
                post_data = json_data.encode('utf-8')
                headers = {}
                headers['Content-Type'] = 'application/json'
                req = urllib.request.Request(url, post_data, headers)
                res = urllib.request.urlopen(req)
		'''

	def validate(self):
		self.check_duplicate_item()
		self.update_price_list_details()
		self.update_item_details()

	def update_price_list_details(self):
		self.doc.buying_or_selling, self.doc.currency = webnotes.conn.get_value("Price List", 
			self.doc.price_list, ["buying_or_selling", "currency"])

	def update_item_details(self):
		self.doc.item_name, self.doc.item_description = webnotes.conn.get_value("Item", 
			self.doc.item_code, ["item_name", "description"])

	def check_duplicate_item(self):
		if webnotes.conn.sql("""select name from `tabItem Price` 
			where item_code=%s and price_list=%s and name!=%s""", 
			(self.doc.item_code, self.doc.price_list, self.doc.name)):
				webnotes.throw("{duplicate_item}: {item_code}, {already}: {price_list}".format(**{
					"duplicate_item": _("Duplicate Item"),
					"item_code": self.doc.item_code,
					"already": _("already available in Price List"),
					"price_list": self.doc.price_list
				}), ItemPriceDuplicateItem)
				
