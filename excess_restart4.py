import csv
from difflib import SequenceMatcher
import os

"""
This script is for Minimal Excess quotes where having the lowest excess is the main priority for the customer.
Cost will not be considered as a factor when it comes to which parts to override.

A separate script, or an adjustment to the parameteres of thsi one, will be created to allow for a more hybrid approach
and also accomodate for cost.
"""

def process_excess(partsall_file, excess_dict):
	exc_header = partsall_file.readline().rstrip('\n').split('\t')
	for line in partsall_file:
		fields = line.strip('\n').split('\t')
		d = dict(zip(exc_header, fields))
		pline = Parts(d)

		#skip part if data is missing
		if pline.costone is None or pline.moq is None: continue
		else:
			#if this is the first time the part is seen, check if it should be seected and exclude from further analysis
			if pline.partnum not in exclusions and int(pline.moq) <= int(pline.volumeone) and pline.partnum not in part_count:
				exclusions.append(pline.partnum)
			#if the above is false, check to see if the excess drop validates switching suppliers
			elif pline.partnum in excess_dict and pline.partnum not in exclusions:
				current_excess = (float(pline.moq) - float(pline.volumeone)) * pline.costone
				if int(pline.moq) == int(excess_dict[pline.partnum]['MOQ']) or int(excess_dict[pline.partnum]['MOQ']) <= int(pline.volumeone): continue
				#if excess is lower than currently selected supplier and moq was not already below vol1, swap. Set flag to 0
				elif current_excess < excess_dict[pline.partnum]['excess']:
					excess_dict[pline.partnum] = {'Supplier': pline.supplier, 'vol1': pline.volumeone, 'cost1': pline.costone,
					'MOQ': pline.moq, 'MPN': pline.mpn, 'excess': current_excess, 'flag': 0}
			#if part was not on any list, then add new entry into the dict. Set flag to 1 so we know it is the first occurance
			elif pline.partnum not in exclusions:
				current_excess = (float(pline.moq) - float(pline.volumeone)) * pline.costone
				excess_dict[pline.partnum] = {'Supplier': pline.supplier, 'vol1': pline.volumeone, 'cost1': pline.costone,
							'MOQ': pline.moq, 'MPN': pline.mpn, 'excess': current_excess, 'flag': 1}
			#keep track of the occurance of each part, ensures that parts with only 1 quote can be removed later
			part_count[pline.partnum] = part_count.get(pline.partnum, 0) + 1

def mpn_deviations(partselect_file, dev_dict):
	dev_header = partselect_file.readline().rstrip('\n').split('\t')
	for line in partselect_file:
		fields = line.strip('\n').split('\t')
		d = dict(zip(dev_header, fields))
		pline = Parts(d)
		unique = '{0}_{1}_{2}'.format(pline.partnum, pline.supplier, pline.mpn)
		
		#set case situations and the appropriate flagging based on the ratio between mpn and cmpn
		if pline.cmpn != None:
			m = SequenceMatcher(None, pline.mpn, pline.cmpn)
			if m.ratio() < .5:
				dev_dict[unique] = {'desc': pline.desc, 'mfr': pline.mfr, 'cmpn': pline.cmpn, 
				'level': 'Very Different'}
			elif m.ratio() < .7:
				dev_dict[unique] = {'desc': pline.desc, 'mfr': pline.mfr, 'cmpn': pline.cmpn, 
				'level': 'Different'}
			elif m.ratio() < .9:
				dev_dict[unique] = {'desc': pline.desc, 'mfr': pline.mfr, 'cmpn': pline.cmpn, 
				'level': 'Close'}
			elif m.ratio() < 1:
				dev_dict[unique] = {'desc': pline.desc, 'mfr': pline.mfr, 'cmpn': pline.cmpn, 
				'level': 'Very Close'}
				
def slt_selection(partsall_file, slt_dict):
	slt_header = partsall_file.readline().rstrip('\n').split('\t')
	for line in partsall_file:
		fields = line.strip('\n').split('\t')
		d = dict(zip(slt_header, fields))
		pline = Parts(d)
		
		if pline.costone is None: continue
		else:
			if pline.partnum not in exclusions and pline.partnum not in part_count and int(pline.inventory) > 0:
				exclusions.append(pline.partnum)
			elif pline.partnum not in exclusions:
				if pline.partnum in slt_dict:
					if int(slt_dict[pline.partnum]['Inventory']) == 0:
						if int(pline.inventory) > 0:
							slt_dict[pline.partnum] = {'Description': pline.desc, 'Supplier': pline.supplier, 'Lead Time': pline.leadtime,
							'Inventory': pline.inventory, 'Mfr': pline.mfr, 'MPN': pline.mpn, 'flag': 0}
					if int(slt_dict[pline.partnum]['Inventory']) == 0 and int(pline.inventory) == 0:
						if int(slt_dict[pline.partnum]['Lead Time']) > pline.leadtime:
							slt_dict[pline.partnum] = {'Description': pline.desc, 'Supplier': pline.supplier, 'Lead Time': pline.leadtime,
								'Inventory': pline.inventory, 'Mfr': pline.mfr, 'MPN': pline.mpn, 'flag': 0}
				else:
					slt_dict[pline.partnum] = {'Description': pline.desc, 'Supplier': pline.supplier, 'Lead Time': pline.leadtime,
								'Inventory': pline.inventory, 'Mfr': pline.mfr, 'MPN': pline.mpn, 'flag': 1}
			part_count[pline.partnum] = part_count.get(pline.partnum, 0) + 1
	
#write out excess_dict to a csv file using the fieldnames previously defined
def write_excessfile(excess_dict, exc_fieldnames, part_count):
	with open(os.path.join('Output','excess_parts.csv'), 'wb') as f:
		w = csv.DictWriter(f, fieldnames=exc_fieldnames)
		w.writeheader()
		for x in excess_dict.keys():
			if part_count[x] == 1 or excess_dict[x]['flag'] == 1 : continue
			else:
				w.writerow({'Part Number': x, 'Supplier' : excess_dict[x]['Supplier'], 'MOQ': excess_dict[x]['MOQ'],
					'Cost One':excess_dict[x]['cost1'], 'MPN' : excess_dict[x]['MPN']})
			#can change this later to be in the upload format to make it easy for teammates

def write_devfile(dev_dict, dev_fieldnames):
	with open(os.path.join('Output', 'deviations.csv'), 'wb') as f:
		w = csv.DictWriter(f, fieldnames=dev_fieldnames)
		w.writeheader()
		for x in dev_dict.keys():
			partnum, supplier, mpn = x.split('_') 
			w.writerow({'Part Number': partnum, 'Description': dev_dict[x]['desc'], 
				'Mfr': dev_dict[x]['mfr'], 'MPN' : mpn, 'Corrected MPN': dev_dict[x]['cmpn'], 
				'Level': dev_dict[x]['level']})

def write_sltfile(slt_dict, slt_fieldnames):
	with open(os.path.join('Output', 'slt.csv'), 'wb') as f:
		w = csv.DictWriter(f, fieldnames=slt_fieldnames)
		w.writeheader()
		for x in slt_dict.keys():
			#if part_count[x] == 1 or slt_dict[x]['flag'] == 1 : continue
			#else:
			w.writerow({'Part Number': x, 'Description': slt_dict[x]['Description'], 'Lead Time': slt_dict[x]['Lead Time'], 
				'Inventory': slt_dict[x]['Inventory'], 'Supplier' : slt_dict[x]['Supplier'],
				'Mfr': slt_dict[x]['Mfr'], 'MPN' : slt_dict[x]['MPN']})			
			
#instantiates an instance of parts consisting of a row of data
class Parts:
	def __init__(self, d):
		self.partnum = d['Part Number']
		self.desc = d['Description']
		self.leadtime = d['Lead Time'] if d['Lead Time'] != '' else None
		self.inventory = d['Inventory'] if d['Inventory'] != '' else 0
		self.supplier = d['Supp Name']
		self.mfr = d['Mfg Name']
		self.volumeone = d['Volume #1']
		self.costone = float(d['Cost #1']) if d['Cost #1'] != '' else None
		self.moq = d['MOQ'] if d['MOQ'] != "" else None
		self.mpn = d['Mfg Part Number']
		self.cmpn = d['Corrected MPN'] if d['Corrected MPN'] != '' else None

exclusions = []
part_count = {}		
		
#define the fieldnames to be used when writing out the file
exc_fieldnames = ['Part Number', 'Supplier', 'MOQ', 'Cost One','MPN']
dev_fieldnames = ['Part Number', 'Description', 'Mfr', 'MPN', 'Corrected MPN', 'Level']
slt_fieldnames = ['Part Number', 'Description', 'Lead Time', 'Inventory', 'Supplier', 'Mfr', 'MPN']

#set up dict's and file names
excess_dict = {}
dev_dict = {}
slt_dict = {}

partsall_file = open(os.path.join('Input', raw_input('Parts All File Name: ')))
partselect_file = open(os.path.join('Input', raw_input('Parts Select File Name: ')))

action = raw_input('type 1 for MPN Deviation List\ntype 2 for Excess Overrides\ntype 3 for Shortest Lead Time Overrides\n')

if int(action) == 1:
	#close dev file and call function to read/write deviations
	mpn_deviations(partselect_file, dev_dict)
	write_devfile(dev_dict, dev_fieldnames)
elif int(action) == 2:
	#close excess file and call function to read/wirte excess overrides
	process_excess(partsall_file, excess_dict)
	write_excessfile(excess_dict, exc_fieldnames, part_count)
elif int(action) == 3:
	#close slt file and call function to read/write shortest lead times
	slt_selection(partsall_file, slt_dict)
	write_sltfile(slt_dict, slt_fieldnames)
else:
	print ('That is not a valid entry, please try again')

partsall_file.close()
partselect_file.close()