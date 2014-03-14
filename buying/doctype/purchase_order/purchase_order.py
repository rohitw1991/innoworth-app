#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt,auth,document_attach
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
from webnotes.utils.html_file import html_data
import os
from webnotes.model.doc import Document, addchild
from cgi_module.doctype.cgi.cgi import attach_file
	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Purchase Order Item'
		self.fname = 'po_details'
		self.status_updater = [{
			'source_dt': 'Purchase Order Item',
			'target_dt': 'Material Request Item',
			'join_field': 'prevdoc_detail_docname',
			'target_field': 'ordered_qty',
			'target_parent_dt': 'Material Request',
			'target_parent_field': 'per_ordered',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
		}]
		
	def validate(self):
		super(DocType, self).validate()
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])

		pc_obj = get_obj(dt='Purchase Common')
		pc_obj.validate_for_items(self)
		pc_obj.get_prevdoc_date(self)
		self.check_for_stopped_status(pc_obj)

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", ["qty", "required_qty"])

		self.validate_with_previous_doc()
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied("po_raw_material_details")
		
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Supplier Quotation": {
				"ref_dn_field": "supplier_quotation",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Supplier Quotation Item": {
				"ref_dn_field": "supplier_quotation_item",
				"compare_fields": [["import_rate", "="], ["project_name", "="], ["item_code", "="], 
					["uom", "="]],
				"is_child_table": True
			}
		})

	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	def get_schedule_dates(self):
		for d in getlist(self.doclist, 'po_details'):
			if d.prevdoc_detail_docname and not d.schedule_date:
				d.schedule_date = webnotes.conn.get_value("Material Request Item",
						d.prevdoc_detail_docname, "schedule_date")
	
	def get_last_purchase_rate(self):
		get_obj('Purchase Common').get_last_purchase_rate(self)

	# Check for Stopped status 
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in getlist(self.doclist, 'po_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

		
	def update_bin(self, is_submit, is_stopped = 0):
		from stock.utils import update_bin
		pc_obj = get_obj('Purchase Common')
		for d in getlist(self.doclist, 'po_details'):
			#1. Check if is_stock_item == 'Yes'
			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				# this happens when item is changed from non-stock to stock item
				if not d.warehouse:
					continue
				
				ind_qty, po_qty = 0, flt(d.qty) * flt(d.conversion_factor)
				if is_stopped:
					po_qty = flt(d.qty) > flt(d.received_qty) and \
						flt( flt(flt(d.qty) - flt(d.received_qty))*flt(d.conversion_factor)) or 0 
				
				# No updates in Material Request on Stop / Unstop
				if cstr(d.prevdoc_doctype) == 'Material Request' and not is_stopped:
					# get qty and pending_qty of prevdoc 
					curr_ref_qty = pc_obj.get_qty(d.doctype, 'prevdoc_detail_docname',
					 	d.prevdoc_detail_docname, 'Material Request Item', 
						'Material Request - Purchase Order', self.doc.name)
					max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
					 	flt(curr_ref_qty.split('~~~')[0]), 0
					
					if flt(qty) + flt(po_qty) > flt(max_qty):
						curr_qty = flt(max_qty) - flt(qty)
						# special case as there is no restriction 
						# for Material Request - Purchase Order 
						curr_qty = curr_qty > 0 and curr_qty or 0
					else:
						curr_qty = flt(po_qty)
					
					ind_qty = -flt(curr_qty)

				# Update ordered_qty and indented_qty in bin
				args = {
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"ordered_qty": (is_submit and 1 or -1) * flt(po_qty),
					"indented_qty": (is_submit and 1 or -1) * flt(ind_qty),
					"posting_date": self.doc.transaction_date
				}
				update_bin(args)
				
	def check_modified_date(self):
		mod_db = sql("select modified from `tabPurchase Order` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception

	def update_status(self, status):
		self.check_modified_date()
		# step 1:=> Set Status
		webnotes.conn.set(self.doc,'status',cstr(status))

		# step 2:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# step 3:=> Acknowledge user
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)))

	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)
		
		self.update_prevdoc_status()
		self.update_bin(is_submit = 1, is_stopped = 0)
		
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, 
			self.doc.company, self.doc.grand_total)
		
		purchase_controller.update_last_purchase_rate(self, is_submit = 1)
		
		webnotes.conn.set(self.doc,'status','Submitted')
		self.create_file()
	 
	def on_cancel(self):
		pc_obj = get_obj(dt = 'Purchase Common')		
		self.check_for_stopped_status(pc_obj)
		
		# Check if Purchase Receipt has been submitted against current Purchase Order
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Receipt', docname = self.doc.name, detail_doctype = 'Purchase Receipt Item')

		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_order = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		webnotes.conn.set(self.doc,'status','Cancelled')
		self.update_prevdoc_status()
		self.update_bin( is_submit = 0, is_stopped = 0)
		pc_obj.update_last_purchase_rate(self, is_submit = 0)
				
	def on_update(self):
		pass
		
	def create_file(self):
		child_data=sql("select item_code,description,sum(qty) as qty,stock_uom,import_rate,sum(import_amount) as import_amount from `tabPurchase Order Item` where parent='"+self.doc.name+"' group by item_code",as_dict=1)
		html=""
		j=0
		for r in child_data:
			j=j+1
			webnotes.errprint(r)
			html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(j)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(r['item_code'])+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(r['description'])+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(r['qty'])+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(r['stock_uom'])+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(r['import_rate'])+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(r['import_amount'])+"</div></td></tr>")

		tax_html=""
		tax_data=sql("select description,tax_amount from `tabPurchase Taxes and Charges` where parent='"+self.doc.name+"'",as_dict=1)
		for tax in tax_data:
			tax_html+=("<tr><td style='width:50%;'>"+tax['description']+"</td><td style='width:50%;text-align:right;'>₹ "+cstr(tax['tax_amount'])+"</td></tr>")
		a=html_data({"posting_date":self.doc.transaction_date,"due_date":"","customer_name":self.doc.customer_name,"net_total":cstr(self.doc.net_total_import),"grand_total":cstr(self.doc.grand_total_import),"rounded_total":cstr(self.doc.grand_total_import),"table_data":html,"date_1":"Purchase Order Date","date_2":"","doctype":"Purchase Order","doctype_no":self.doc.name,"company":self.doc.company,"addr_name":"Address","address":self.doc.customer_address,"tax_detail":tax_html})
                attach_file(a,[self.doc.name,"Buying/Kirana","Purchase Order"])
		
	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)

@webnotes.whitelist()
def make_purchase_receipt(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.import_amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.import_rate)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.purchase_rate)

	doclist = get_mapped_doclist("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Receipt", 
			"validation": {
				"docstatus": ["=", 1],
			}
		}, 
		"Purchase Order Item": {
			"doctype": "Purchase Receipt Item", 
			"field_map": {
				"name": "prevdoc_detail_docname", 
				"parent": "prevdoc_docname", 
				"parenttype": "prevdoc_doctype", 
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.received_qty < doc.qty
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_purchase_invoice(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.run_method("set_missing_values")
		bean.run_method("set_supplier_defaults")

	def update_item(obj, target, source_parent):
		target.import_amount = flt(obj.import_amount) - flt(obj.billed_amt)
		target.amount = target.import_amount * flt(source_parent.conversion_rate)
		if flt(obj.purchase_rate):
			target.qty = target.amount / flt(obj.purchase_rate)

	doclist = get_mapped_doclist("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Invoice", 
			"validation": {
				"docstatus": ["=", 1],
			}
		}, 
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item", 
			"field_map": {
				"name": "po_detail", 
				"parent": "purchase_order", 
				"purchase_rate": "rate"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.amount==0 or doc.billed_amt < doc.import_amount 
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]
