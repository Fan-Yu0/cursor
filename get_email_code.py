import logging
import time
import re
from config import Config
import requests
import email
import imaplib


class EmailVerificationHandler:
    def __init__(self):
        self.imap = Config().get_imap()
        self.session = requests.Session()


    # 使用imap获取邮件
    def get_mail_code_by_imap(self, retry = 0):
        if retry > 0:
            time.sleep(3)
        if retry >= 20:
            raise Exception("获取验证码超时")
        try:
            # 连接到IMAP服务器
            mail = imaplib.IMAP4_SSL(self.imap['imap_server'], self.imap['imap_port'])
            mail.login(self.imap['imap_user'], self.imap['imap_pass'])
            mail.select(self.imap['imap_dir'])

            status, messages = mail.search(None, 'FROM', '"no-reply@cursor.sh"')
            if status != 'OK':
                return None

            mail_ids = messages[0].split()
            if not mail_ids:
                # 没有获取到，就在获取一次
                return self.get_mail_code_by_imap(retry=retry + 1)

            latest_mail_id = mail_ids[-1]

            # 获取邮件内容
            status, msg_data = mail.fetch(latest_mail_id, '(RFC822)')
            if status != 'OK':
                return None

            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # 提取邮件正文
            body = self._extract_imap_body(email_message)
            if body:
                # 使用正则表达式查找6位数字验证码
                code_match = re.search(r"\b\d{6}\b", body)
                if code_match:
                    code = code_match.group()
                    # 删除邮件
                    mail.store(latest_mail_id, '+FLAGS', '\\Deleted')
                    mail.expunge()
                    mail.logout()
                    # print(f"找到的验证码: {code}")
                    return code
            # print("未找到验证码")
            mail.logout()
            return None
        except Exception as e:
            print(f"发生错误: {e}")
            return None


    def _extract_imap_body(self, email_message):
        # 提取邮件正文
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        return body
                    except Exception as e:
                        logging.error(f"解码邮件正文失败: {e}")
        else:
            content_type = email_message.get_content_type()
            if content_type == "text/plain":
                charset = email_message.get_content_charset() or 'utf-8'
                try:
                    body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
                    return body
                except Exception as e:
                    logging.error(f"解码邮件正文失败: {e}")
        return ""


if __name__ == "__main__":
    email_handler = EmailVerificationHandler()
    code = email_handler.get_mail_code_by_imap()
    print(code)
