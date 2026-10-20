from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import SerialandBatchBundle


class OvrSerialandBatchBundle(SerialandBatchBundle):
    def validate_incorrect_serial_nos(self, serial_nos):
        # serial nos may be moved between items (machines are re-coded), so this check is skipped
        pass

    # NOTE: the v15 overrides of set_incoming_rate_for_inward_transaction / fetch_outward_entry_rate are gone:
    # v16 ERPNext takes the outward rate + additional cost for Stock Entry transfers itself (get_transfer_rates).
