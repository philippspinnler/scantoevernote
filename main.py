from dataclasses import dataclass
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)
import os
import base64
import datetime
import shutil
from time import sleep


ROOT_DIR = os.environ.get("ROOT_DIR")
SENDGRIP_API_KEY = os.environ.get("SENDGRIP_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
EVERNOTE_EMAIL_ADDRESS = os.environ.get("EVERNOTE_EMAIL_ADDRESS")
EVERNOTE_NOTE_BOOK = os.environ.get("EVERNOTE_NOTE_BOOK", "Dokumente")
PROCESSED_FOLDER = os.environ.get("PROCESSED_FOLDER", "processed")
PROCESS_INTERVALI_IN_SECONDS = os.environ.get("PROCESS_INTERVALI_IN_SECONDS", 10)


@dataclass
class UnprocessedFile:
    category: str
    file_path: str
    dir_path: str
    file_name: str


def get_unprocessed_files() -> list[UnprocessedFile]:
    unprocessed_files: list[UnprocessedFile] = []
    for sub_folder_name in os.listdir(ROOT_DIR):
        sub_folder_path = os.path.join(ROOT_DIR, sub_folder_name)
        if os.path.isdir(sub_folder_path):
            for file_name in os.listdir(sub_folder_path):
                file_path = os.path.join(sub_folder_path, file_name)
                if os.path.isfile(file_path):
                    if not file_name.lower().endswith(".pdf"):
                        continue
                    unprocessed_files.append(
                        UnprocessedFile(
                            category=sub_folder_name,
                            file_path=file_path,
                            dir_path=sub_folder_path,
                            file_name=file_name,
                        )
                    )

    return unprocessed_files


def get_base64_encoded_file_content(file_path: str) -> str:
    with open(file_path, "rb") as file:
        encoded_string = base64.b64encode(file.read())

    return encoded_string.decode("utf-8")


def send_email(recipient: str, subject: str, attachment: Attachment):
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=recipient,
        subject=subject,
        html_content=" ",
    )

    message.add_attachment(attachment)
    sg = SendGridAPIClient(SENDGRIP_API_KEY)
    sg.send(message)


def creation_date(path_to_file) -> str:
    str_format = "%Y%m%d%H%M%S"
    stat = os.stat(path_to_file)
    try:
        return datetime.datetime.fromtimestamp(stat.st_birthtime).strftime(str_format)
    except AttributeError:
        return datetime.datetime.fromtimestamp(stat.st_mtime).strftime(str_format)


def move_processed_file(unprocessed_file: UnprocessedFile):
    processed_path = os.path.join(unprocessed_file.dir_path, PROCESSED_FOLDER)
    if not os.path.exists(processed_path):
        os.makedirs(processed_path)

    shutil.move(unprocessed_file.file_path, processed_path)


if __name__ == "__main__":
    while True:
        unprocessed_files = get_unprocessed_files()
        for unprocessed_file in unprocessed_files:
            subject = f"{creation_date(unprocessed_file.file_path)} - {unprocessed_file.file_name} @{EVERNOTE_NOTE_BOOK} #{unprocessed_file.category}"
            attachment = Attachment(
                FileContent(
                    get_base64_encoded_file_content(unprocessed_file.file_path)
                ),
                FileName(unprocessed_file.file_name),
                FileType("application/pdf"),
                Disposition("attachment"),
            )
            try:
                send_email(
                    recipient=EVERNOTE_EMAIL_ADDRESS,
                    subject=subject,
                    attachment=attachment,
                )
            except Exception as e:
                print(f"Not able to send file to evernote - {e}")
                continue
            move_processed_file(unprocessed_file)
            print(f"Processed file {unprocessed_file.file_path}")
        sleep(PROCESS_INTERVALI_IN_SECONDS)
