"""Create a helpdesk ticket by sending an email through the helpdesk mailbox."""

from __future__ import print_function

import argparse
import smtplib
from email.mime.text import MIMEText
from six.moves import configparser


CONFIG_PATH = r"G:\globals\pipelineConfigs\mail"
ERROR_TICKET_SUBJECT = "[SGD] CRITICAL - SG event daemon."


def format_error_ticket(record, error_details):
    """Build a ticket from a log record and its optional ShotGrid event data."""
    def mapping(value):
        return value if isinstance(value, dict) else {}

    def text(value):
        if value is None:
            return ""
        try:
            return " ".join(str(value).split())
        except Exception:
            return ""

    def link(value):
        value = mapping(value)
        name, identifier = text(value.get("name")), text(value.get("id"))
        return " ".join(part for part in (name, "(%s)" % identifier if identifier else "") if part)

    event = mapping(getattr(record, "shotgrid_event", None))
    entity = mapping(event.get("entity"))
    entity_name = text(entity.get("name"))
    entity_id = text(entity.get("id"))
    entity_label = " ".join(part for part in (
        text(entity.get("type")),
        '\u201c%s\u201d' % entity_name if entity_name else "",
        "(%s)" % entity_id if entity_id else "",
    ) if part)
    fields = [
        ("Project", link(event.get("project"))),
        ("Plugin/logger", text(getattr(record, "name", None))),
        ("Event", text(event.get("event_type"))),
        ("Changed field", text(event.get("attribute_name")) or
         text(mapping(event.get("meta")).get("attribute_name"))),
        ("Entity", entity_label),
        ("Event ID", text(event.get("id"))),
        ("Triggered by", text(mapping(event.get("user")).get("name"))),
    ]
    summary = "\n".join("%s: %s" % (label, value) for label, value in fields if value)
    original = "Full technical details:\n" + error_details
    return ERROR_TICKET_SUBJECT, summary + "\n\n" + original if summary else original


def read_mail_config(config_path=CONFIG_PATH):
    """Return the SMTP settings for the configured helpdesk mailbox."""
    config = configparser.ConfigParser()
    if not config.read(config_path):
        raise IOError("Could not read mail configuration: %s" % config_path)

    return {
        "addr": config.get("helpdesk_mail", "addr"),
        "pw": config.get("helpdesk_mail", "pw"),
        "server": config.get("helpdesk_mail", "server"),
        "port": config.getint("helpdesk_mail", "port"),
    }


def create_ticket(subject, body, config_path=CONFIG_PATH):
    """Send a UTF-8 plain-text ticket to the helpdesk mailbox."""
    mail_config = read_mail_config(config_path)
    sender = mail_config["addr"]

    message = MIMEText(body, "plain", "utf-8")
    message["From"] = sender
    message["To"] = sender
    message["Subject"] = subject

    with smtplib.SMTP(mail_config["server"], mail_config["port"]) as server:
        server.starttls()
        server.login(sender, mail_config["pw"])
        server.sendmail(sender, [sender], message.as_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help="ticket email subject")
    parser.add_argument("body", help="plain-text ticket body")
    args = parser.parse_args()
    create_ticket(args.subject, args.body)


if __name__ == "__main__":
    main()
