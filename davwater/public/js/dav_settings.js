// Client side access to Dav Water Settings values (cached for the session).
frappe.provide("davwater.settings");

davwater.settings._cache = {};

davwater.settings.get = function (fieldname) {
	const cache = davwater.settings._cache;
	if (!(fieldname in cache)) {
		cache[fieldname] = frappe.xcall("davwater.hook_event.util.get_dav_setting_value", { fieldname });
	}
	return cache[fieldname];
};

// Set the Leasing Cost Center on every item row. Does nothing when the setting is blank.
davwater.settings.set_leasing_cost_center = async function (frm) {
	const cost_center = await davwater.settings.get("leasing_cost_center");
	if (!cost_center) return;
	(frm.doc.items || []).forEach(function (item) {
		frappe.model.set_value(item.doctype, item.name, "cost_center", cost_center);
	});
};
