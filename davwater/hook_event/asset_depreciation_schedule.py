from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	AssetDepreciationSchedule,
)


class OverrideAssetDepreciationSchedule(AssetDepreciationSchedule):
	def _check_is_pro_rata(self):
		# Straight Line assets are never pro-rated; all other methods use the standard logic
		if self.fb_row.depreciation_method == "Straight Line":
			self.has_pro_rata = False
			self.has_wdv_or_dd_non_yearly_pro_rata = False
			return

		super()._check_is_pro_rata()
