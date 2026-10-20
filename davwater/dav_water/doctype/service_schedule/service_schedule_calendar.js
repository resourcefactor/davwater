frappe.views.calendar["Service Schedule"] = {
	field_map: {
		"start": "from_date",
		"end": "to_date",
		"id": "name",
		"title": "title",
		"docstatus": 1
	},
	get_events_method: "davwater.dav_water.doctype.service_schedule.service_schedule.get_events"
}