"""Create a helpdesk ticket by sending an email through the helpdesk mailbox."""

from __future__ import print_function

import argparse
import smtplib
from email.mime.text import MIMEText
from six.moves import configparser


CONFIG_PATH = r"G:\globals\pipelineConfigs\mail"


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