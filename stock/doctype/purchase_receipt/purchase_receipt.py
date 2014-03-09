#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, cint, nowdate,nowtime,auth,document_attach
from utilities.transaction_base import get_default_address, get_address_display
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _
from webnotes.model.doc import Document, addchild
import webnotes.defaults
import datetime
from stock.utils import update_bin
from webnotes.utils.html_file import html_data
import os

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Purchase Receipt Item'
		self.fname = 'purchase_receipt_details'
		self.count = 0
		self.status_updater = [{
			'source_dt': 'Purchase Receipt Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'prevdoc_detail_docname',
			'target_field': 'received_qty',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_received',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
		}]
		
	def onload(self):
		billed_qty = webnotes.conn.sql("""select sum(ifnull(qty, 0)) from `tabPurchase Invoice Item`
			where purchase_receipt=%s""", self.doc.name)
		if billed_qty:
			total_qty = sum((item.qty for item in self.doclist.get({"parentfield": "purchase_receipt_details"})))
			self.doc.fields["__billing_complete"] = billed_qty[0][0] == total_qty

	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	def validate(self):
		super(DocType, self).validate()
		
		self.po_required()

		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Cancelled"])

		self.validate_with_previous_doc()
		self.validate_rejected_warehouse()
		self.validate_accepted_rejected_qty()
		self.validate_inspection()
		self.validate_uom_is_integer("uom", ["qty", "received_qty"])
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_challan_no()

		pc_obj = get_obj(dt='Purchase Common')
		pc_obj.validate_for_items(self)
		pc_obj.get_prevdoc_date(self)
		self.check_for_stopped_status(pc_obj)

		# sub-contracting
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied("pr_raw_material_details")
		
		self.update_valuation_rate("purchase_receipt_details")

	def validate_rejected_warehouse(self):
		for d in self.doclist.get({"parentfield": "purchase_receipt_details"}):
			if flt(d.rejected_qty) and not d.rejected_warehouse:
				d.rejected_warehouse = self.doc.rejected_warehouse
				if not d.rejected_warehouse:
					webnotes.throw(_("Rejected Warehouse is mandatory against regected item"))		

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in getlist(self.doclist, "purchase_receipt_details"):
			if not flt(d.received_qty) and flt(d.qty):
				d.received_qty = flt(d.qty) - flt(d.rejected_qty)

			elif not flt(d.qty) and flt(d.rejected_qty):
				d.qty = flt(d.received_qty) - flt(d.rejected_qty)

			elif not flt(d.rejected_qty):
				d.rejected_qty = flt(d.received_qty) -  flt(d.qty)

			# Check Received Qty = Accepted Qty + Rejected Qty
			if ((flt(d.qty) + flt(d.rejected_qty)) != flt(d.received_qty)):

				msgprint("Sum of Accepted Qty and Rejected Qty must be equal to Received quantity. Error for Item: " + cstr(d.item_code))
				raise Exception


	def validate_challan_no(self):
		"Validate if same challan no exists for same supplier in a submitted purchase receipt"
		if self.doc.challan_no:
			exists = webnotes.conn.sql("""
			SELECT name FROM `tabPurchase Receipt`
			WHERE name!=%s AND supplier=%s AND challan_no=%s
		AND docstatus=1""", (self.doc.name, self.doc.supplier, self.doc.challan_no))
			if exists:
				webnotes.msgprint("Another Purchase Receipt using the same Challan No. already exists.\
			Please enter a valid Challan No.", raise_exception=1)
			
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Purchase Order": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["supplier", "="], ["company", "="],	["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "prevdoc_detail_docname",
				"compare_fields": [["project_name", "="], ["uom", "="], ["item_code", "="]],
				"is_child_table": True
			}
		})
		
		if cint(webnotes.defaults.get_global_default('maintain_same_rate')):
			super(DocType, self).validate_with_previous_doc(self.tname, {
				"Purchase Order Item": {
					"ref_dn_field": "prevdoc_detail_docname",
					"compare_fields": [["import_rate", "="]],
					"is_child_table": True
				}
			})
			

	def po_required(self):
		if webnotes.conn.get_value("Buying Settings", None, "po_required") == 'Yes':
			 for d in getlist(self.doclist,'purchase_receipt_details'):
				 if not d.prevdoc_docname:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	def update_stock(self):
		sl_entries = []
		stock_items = self.get_stock_items()
		
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)
				
				if pr_qty:
					sl_entries.append(self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
				
				if flt(d.rejected_qty) > 0:
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": d.rejected_warehouse,
						"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
						"serial_no": cstr(d.rejected_serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
						
		self.bk_flush_supp_wh(sl_entries)
		self.make_sl_entries(sl_entries)

	def create_dn(self):
		dn=Document('Delivery Note')
		dn.customer=self.doc.customer
		dn.customer_name=webnotes.conn.get_value("Customer",self.doc.customer,"customer_name")		
		dn.company='InnoWorth'
                dn.conversion_rate=1.00
		dn.posting_date=nowdate()
		dn.posting_time=nowtime()
		dn.customer_address=webnotes.conn.get_value("Address",{"customer":self.doc.customer},"name")
		dn.address_display=get_address_display(dn.customer_address)
		dn.price_list_currency='INR'
                dn.currency='INR'
		dn.docstatus=1
		dn.status="Submitted"
                dn.selling_price_list='Standard Selling'
                dn.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
		dn.save()
		j=0
		html=""
		net_tot=0.00
		for s in getlist(self.doclist,"purchase_receipt_details"):
			j=j+1
			dni=Document("Delivery Note Item")
			dni.item_code=s.item_code
			dni.item_name=s.item_name
			dni.description=s.description
			dni.qty=s.qty
			dni.ref_rate=webnotes.conn.get_value("Item Price",{"item_code":dni.item_code,"price_list":"Standard Selling"},"ref_rate")
                        dni.export_rate=webnotes.conn.get_value("Item Price",{"item_code":dni.item_code,"price_list":"Standard Selling"},"ref_rate")
			dni.export_amount=cstr(flt(s.qty)*flt(dni.ref_rate))
			net_tot=cstr(flt(net_tot)+flt(dni.export_amount))
			dni.warehouse=s.warehouse
			dni.stock_uom=s.uom
			dni.serial_no=s.serial_no
			dni.parent=dn.name
			dni.save()
			update_bin=("update tabBin set actual_qty=actual_qty-"+cstr(dni.qty)+" and projected_qty=projected_qty-"+cstr(dni.qty)+" where item_code='"+dni.item_code+"' and warehouse='"+dni.warehouse+"'")
			html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(j)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(dni.item_code)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(dni.description)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(dni.qty)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(dni.stock_uom)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(dni.ref_rate)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(dni.export_amount)+"</div></td></tr>")
			stl=Document("Stock Ledger Entry")
			stl.item_code=s.item_code
			stl.stock_uom=s.uom
			stl.serial_no=s.serial_no
			stl.warehouse=s.warehouse
			stl.posting_date=nowdate()
			stl.voucher_type="Delivery Note"
			stl.voucher_no=dn.name
			stl.voucher_detail_no=dni.name
			stl.is_cancelled="No"
			stl.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
			stl.actual_qty=cstr(s.qty)
			qty=webnotes.conn.sql("select qty_after_transaction from `tabStock Ledger Entry` where item_code='"+s.item_code+"' and warehouse='"+s.warehouse+"' order by name desc limit 1",as_list=1)
			stl.qty_after_transaction=cstr(flt(qty[0][0])-flt(s.qty))
			stl.save()
			if dni.serial_no:
				for s in dni.serial_no:
					update=webnotes.conn.sql("update `tabSerial No` set status='Delivered', warehouse=(select name from tabCustomer where 1=2) where name='"+s+"'")

		dn_=Document("Delivery Note",dn.name)
		dn_.net_total_export=cstr(net_tot)
                dn_.grand_total_export=cstr(net_tot)
                dn_.rounded_total_export=cstr(net_tot)
		a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":"","customer_name":dn.customer_name,"net_total":dn_.net_total_export,"grand_total":dn_.grand_total_export,"rounded_total":dn_.rounded_total_export,"table_data":html,"date_1":"Posting Date","date_2":"","doctype":"Delivery Note","doctype_no":dn.name,"company":dn.company,"addr_name":"Address","address":dn.address_display,"tax_detail":""})
                attach_file(a,[dn.name,"Selling/Kirana","Delivery Note"])
				
	def update_ordered_qty(self):
		stock_items = self.get_stock_items()
		for d in self.doclist.get({"parentfield": "purchase_receipt_details"}):
			if d.item_code in stock_items and d.warehouse \
					and cstr(d.prevdoc_doctype) == 'Purchase Order':
									
				already_received_qty = self.get_already_received_qty(d.prevdoc_docname, 
					d.prevdoc_detail_docname)
				po_qty, ordered_warehouse = self.get_po_qty_and_warehouse(d.prevdoc_detail_docname)
				
				if not ordered_warehouse:
					webnotes.throw(_("Warehouse is missing in Purchase Order"))
				
				if already_received_qty + d.qty > po_qty:
					ordered_qty = - (po_qty - already_received_qty) * flt(d.conversion_factor)
				else:
					ordered_qty = - flt(d.qty) * flt(d.conversion_factor)
				
				update_bin({
					"item_code": d.item_code,
					"warehouse": ordered_warehouse,
					"posting_date": self.doc.posting_date,
					"ordered_qty": flt(ordered_qty) if self.doc.docstatus==1 else -flt(ordered_qty)
				})

	def get_already_received_qty(self, po, po_detail):
		qty = webnotes.conn.sql("""select sum(qty) from `tabPurchase Receipt Item` 
			where prevdoc_detail_docname = %s and docstatus = 1 
			and prevdoc_doctype='Purchase Order' and prevdoc_docname=%s 
			and parent != %s""", (po_detail, po, self.doc.name))
		return qty and flt(qty[0][0]) or 0.0
		
	def get_po_qty_and_warehouse(self, po_detail):
		po_qty, po_warehouse = webnotes.conn.get_value("Purchase Order Item", po_detail, 
			["qty", "warehouse"])
		return po_qty, po_warehouse
	
	def bk_flush_supp_wh(self, sl_entries):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			# negative quantity is passed as raw material qty has to be decreased 
			# when PR is submitted and it has to be increased when PR is cancelled
			sl_entries.append(self.get_sl_entries(d, {
				"item_code": d.rm_item_code,
				"warehouse": self.doc.supplier_warehouse,
				"actual_qty": -1*flt(d.consumed_qty),
				"incoming_rate": 0
			}))

	def validate_inspection(self):
		for d in getlist(self.doclist, 'purchase_receipt_details'):		 #Enter inspection date for all items that require inspection
			ins_reqd = webnotes.conn.sql("select inspection_required from `tabItem` where name = %s",
				(d.item_code,), as_dict = 1)
			ins_reqd = ins_reqd and ins_reqd[0]['inspection_required'] or 'No'
			if ins_reqd == 'Yes' and not d.qa_no:
				msgprint("Item: " + d.item_code + " requires QA Inspection. Please enter QA No or report to authorized person to create Quality Inspection")

	# Check for Stopped status
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

	# on submit
	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)

		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total)

		# Set status as Submitted
		webnotes.conn.set(self.doc, 'status', 'Submitted')

		self.update_prevdoc_status()
		
		self.update_ordered_qty()
		
		self.update_stock()

		from stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "purchase_receipt_details")

		purchase_controller.update_last_purchase_rate(self, 1)
		
		self.make_gl_entries()
		self.create_dn()

	def check_next_docstatus(self):
		submit_rv = webnotes.conn.sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Purchase Invoice : " + cstr(self.submit_rv[0][0]) + " has already been submitted !")
			raise Exception , "Validation Error."


	def on_cancel(self):
		pc_obj = get_obj('Purchase Common')

		self.check_for_stopped_status(pc_obj)
		# Check if Purchase Invoice has been submitted against current Purchase Order
		# pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Invoice', docname = self.doc.name, detail_doctype = 'Purchase Invoice Item')

		submitted = webnotes.conn.sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		
		webnotes.conn.set(self.doc,'status','Cancelled')

		self.update_ordered_qty()
		
		self.update_stock()

		self.update_prevdoc_status()
		pc_obj.update_last_purchase_rate(self, 0)
		
		self.make_cancel_gl_entries()
			
	def get_current_stock(self):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			if self.doc.supplier_warehouse:
				bin = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.doc.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0


	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)
		
	def get_gl_entries(self, warehouse_account=None):
		against_stock_account = self.get_company_default("stock_received_but_not_billed")
		
		gl_entries = super(DocType, self).get_gl_entries(warehouse_account, against_stock_account)
		return gl_entries
		

def attach_file(a,path_data):

                #path=self.file_name(path_data[0])
                #html_file= open(path[0],"w")
                import io
                name=path_data[0]
                path=cstr(path_data[0]).replace("/","")
                f = io.open("files/"+path+".html", 'w', encoding='utf8')
                f.write(a)
                f.close()

                s=auth()
                if s[0]=="Done":
                        dms_path=webnotes.conn.sql("select value from `tabSingles` where doctype='LDAP Settings' and field='dms_path'",as_list=1)
                        document_attach("files/"+path+".html",dms_path[0][0]+path_data[1]+"/"+path+".html",s[1],"upload")
                        file_attach=Document("File Data")
                        file_attach.file_name="files/"+path+".html"
                        file_attach.attached_to_doctype=path_data[2]
                        file_attach.file_url=dms_path[0][0]+path_data[1]+"/"+path+".html"
                        file_attach.attached_to_name=name
                        file_attach.save()
                        os.remove("files/"+path+".html")
                        return s[0]
                else:
                        return s[1]


@webnotes.whitelist()
def make_purchase_invoice(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.run_method("set_missing_values")
		bean.run_method("set_supplier_defaults")

	doclist = get_mapped_doclist("Purchase Receipt", source_name,	{
		"Purchase Receipt": {
			"doctype": "Purchase Invoice", 
			"validation": {
				"docstatus": ["=", 1],
			}
		}, 
		"Purchase Receipt Item": {
			"doctype": "Purchase Invoice Item", 
			"field_map": {
				"name": "pr_detail", 
				"parent": "purchase_receipt", 
				"prevdoc_detail_docname": "po_detail", 
				"prevdoc_docname": "purchase_order", 
				"purchase_rate": "rate"
			},
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]
