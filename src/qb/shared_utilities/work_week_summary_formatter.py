"""
Work Week Summary Formatter - Formats weekly summary with vendor, item, and job breakdowns
"""

from typing import Dict, List, Any


class WorkWeekSummaryFormatter:
    """Formats work week summary for display"""

    def __init__(self, width: int = 40):
        self.width = width
        self.separator = "=" * width
        self.line_separator = "-" * width

    def format_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format complete work week summary from processed data

        Args:
            summary_data: Dictionary containing:
                - week_str: Week date range string
                - vendor_data: Dict of vendor -> {total, items: {item -> amount}}
                - item_data: Dict of item -> {total, jobs: {job -> amount}}
                - job_totals: Dict of job -> amount
                - grand_total: Total amount for week

        Returns:
            Formatted summary string
        """
        lines = []

        # Header
        lines.append("WORK WEEK SUMMARY")
        lines.append(f"Week: {summary_data['week_str']}")
        lines.append(self.separator)
        lines.append("")

        vendor_data = summary_data.get('vendor_data', {})
        item_data = summary_data.get('item_data', {})
        job_totals = summary_data.get('job_totals', {})
        grand_total = summary_data.get('grand_total', 0.0)

        if not vendor_data:
            lines.append("No bills found for this week")
            return "\n".join(lines)

        # VENDOR TOTALS section with item breakdown
        lines.append("VENDOR TOTALS:")
        lines.append(self.line_separator)

        for vendor in sorted(vendor_data.keys()):
            vdata = vendor_data[vendor]
            # Vendor name and total
            vendor_line = vendor[:30]
            amount_str = f"${vdata['total']:,.2f}"
            spaces = self.width - len(vendor_line) - len(amount_str)
            lines.append(f"{vendor_line}{' ' * spaces}{amount_str}")

            # Item breakdown for this vendor
            for item in sorted(vdata['items'].keys()):
                item_amount = vdata['items'][item]
                item_line = f"  {item[:28]}"
                amount_str = f"${item_amount:,.2f}"
                spaces = self.width - len(item_line) - len(amount_str)
                lines.append(f"{item_line}{' ' * spaces}{amount_str}")

            lines.append("")  # Blank line between vendors

        lines.append(self.line_separator)
        total_line = "TOTAL"
        amount_str = f"${grand_total:,.2f}"
        spaces = self.width - len(total_line) - len(amount_str)
        lines.append(f"{total_line}{' ' * spaces}{amount_str}")
        lines.append("")
        lines.append(self.separator)
        lines.append("")

        # ITEM TOTALS section with job breakdown
        lines.append("ITEM TOTALS:")
        lines.append(self.line_separator)

        for item in sorted(item_data.keys()):
            idata = item_data[item]
            # Item name and total
            item_line = item[:30]
            amount_str = f"${idata['total']:,.2f}"
            spaces = self.width - len(item_line) - len(amount_str)
            lines.append(f"{item_line}{' ' * spaces}{amount_str}")

            # Job breakdown for this item
            for job in sorted(idata['jobs'].keys()):
                job_amount = idata['jobs'][job]
                job_line = f"  {job[:28]}"
                amount_str = f"${job_amount:,.2f}"
                spaces = self.width - len(job_line) - len(amount_str)
                lines.append(f"{job_line}{' ' * spaces}{amount_str}")

            lines.append("")  # Blank line between items

        lines.append(self.line_separator)
        total_line = "TOTAL"
        amount_str = f"${grand_total:,.2f}"
        spaces = self.width - len(total_line) - len(amount_str)
        lines.append(f"{total_line}{' ' * spaces}{amount_str}")
        lines.append("")
        lines.append(self.separator)
        lines.append("")

        # JOB TOTALS section
        lines.append("JOB TOTALS:")
        lines.append(self.line_separator)

        for job in sorted(job_totals.keys()):
            job_line = job[:30]
            amount_str = f"${job_totals[job]:,.2f}"
            spaces = self.width - len(job_line) - len(amount_str)
            lines.append(f"{job_line}{' ' * spaces}{amount_str}")

        lines.append(self.line_separator)
        total_line = "TOTAL"
        amount_str = f"${grand_total:,.2f}"
        spaces = self.width - len(total_line) - len(amount_str)
        lines.append(f"{total_line}{' ' * spaces}{amount_str}")

        return "\n".join(lines)