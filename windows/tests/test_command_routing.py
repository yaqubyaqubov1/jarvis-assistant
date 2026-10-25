"""Regression tests: users' natural commands must reach the right tool.

No microphone, Gmail account, live Ollama or Windows UI required.
"""
import unittest
from unittest.mock import patch

from core.router import quick_plan
from core.document_planner import plan_document


class NaturalLanguageRoutingTests(unittest.TestCase):
    def check_tool(self, spoken, expected):
        plan = quick_plan(spoken)
        self.assertIsNotNone(plan, spoken)
        self.assertEqual(plan["kind"], "task", plan)
        self.assertEqual(plan["steps"][0]["tool"], expected, plan)
        return plan["steps"][0]["arguments"]

    def test_excel_in_natural_english(self):
        args = self.check_tool(
            "Create an Excel spreadsheet in Documents named expenses.xlsx "
            "with columns Item and Cost and rows Rent 800, Internet 50",
            "create_spreadsheet",
        )
        self.assertEqual(args["path"], "documents/expenses.xlsx")
        self.assertEqual(args["columns"], ["Item", "Cost"])
        self.assertEqual(args["rows"], [["Rent", 800], ["Internet", 50]])

    def test_csv_export_to_desktop(self):
        args = self.check_tool(
            "Make a CSV called inventory.csv on Desktop with columns Item and Count "
            "and rows Pens 5, Pencils 12",
            "create_csv",
        )
        self.assertEqual(args["path"], "desktop/inventory.csv")
        self.assertEqual(len(args["rows"]), 2)

    def test_only_columns(self):
        args = self.check_tool(
            "Create an Excel file named test.xlsx with columns Date, Name and Amount",
            "create_spreadsheet",
        )
        self.assertEqual(args["columns"], ["Date", "Name", "Amount"])
        self.assertEqual(args["rows"], [])

    def test_gmail_summary_variations(self):
        for sentence in (
            "Summarise my emails from the last 24 hours",
            "Summarize my inbox",
            "Check my Gmail",
            "Give me a briefing on my emails",
            "Summarize mails within a 24 hour period",
        ):
            with self.subTest(sentence=sentence):
                self.check_tool(sentence, "gmail_summary_24h")

    def test_send_latest_draft_requires_confirmation(self):
        args = self.check_tool("Send the email", "gmail_send_draft")
        self.assertEqual(args["draft_id"], "last")

    def test_compose_with_address(self):
        args = self.check_tool(
            "Draft an email to team@example.org about our weekly meeting",
            "gmail_prepare_email",
        )
        self.assertEqual(args["to"], "team@example.org")
        self.assertEqual(args["subject"], "our weekly meeting")

    def test_no_recipient_is_not_invented(self):
        plan = quick_plan("Draft an email about the weekly meeting")
        self.assertEqual(plan["kind"], "conversation")
        self.assertIn("recipient", plan["response"])

    def test_account_web_page(self):
        self.check_tool("Summarize this account dashboard", "browser_account_overview")
        self.check_tool("Look at my account page", "browser_account_overview")

    def test_explanation_is_not_file_creation(self):
        self.assertIsNone(quick_plan("How to create an Excel spreadsheet"))

    def test_require_explicit_filename(self):
        plan = quick_plan("Create an Excel spreadsheet")
        self.assertEqual(plan["kind"], "conversation")
        self.assertIn(".xlsx", plan["response"])

    def test_normal_shortcuts_still_work(self):
        self.check_tool("open calculator", "open_application")
        self.check_tool("what time is it", "get_time_date")


class DocumentPlannerTests(unittest.TestCase):
    @patch("core.document_planner.generate")
    def test_word_document_uses_focused_model(self, generate):
        generate.return_value = (
            '{"title":"Quarterly update","content":"Overview",'
            '"sections":[{"heading":"Priorities","body":"Review goals"}]}'
        )
        plan = plan_document(
            "Create a Word report called quarterly.docx about project priorities"
        )
        self.assertEqual(plan["steps"][0]["tool"], "create_word_document")
        self.assertEqual(plan["steps"][0]["arguments"]["path"], "documents/quarterly.docx")

    @patch("core.document_planner.generate")
    def test_presentation_focused_model(self, generate):
        generate.return_value = (
            '{"title":"Briefing","slides":'
            '[{"title":"Overview","bullets":["Status","Next steps"]}]}'
        )
        plan = plan_document(
            "Make a PowerPoint presentation named briefing.pptx about project updates"
        )
        self.assertEqual(plan["steps"][0]["tool"], "create_presentation")

    @patch("core.document_planner.generate")
    def test_invalid_generated_json_does_not_create_file(self, generate):
        generate.return_value = "This is not JSON"
        plan = plan_document("Write a report called status.docx about progress")
        self.assertEqual(plan["kind"], "conversation")
        self.assertEqual(plan["steps"], [])


if __name__ == "__main__":
    unittest.main()
