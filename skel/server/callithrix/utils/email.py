from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

host = port = sender = user = password = None


def init(config):
    global host, port, sender, user, password
    host = config['smtp']['host']
    port = config['smtp']['port']
    sender = config['smtp']['sender']
    user = config['smtp']['user']
    password = config['smtp']['password']


def enviar_email(subject, to, message, reply_to=sender):
    mimetext="html" if message.startswith('<') else "plain"
    if subject == '':
        raise Exception("Tipo de email indefinido!")
    if to == '':
        raise Exception("Endereço de email de destino inválido!")

    server = None

    try:
        server = SMTP(host, port)
        email_msg = MIMEMultipart()
        email_msg['From '] = sender
        email_msg['Subject '] = subject
        email_msg['Reply-To '] = reply_to

        email_msg.attach(MIMEText(message, mimetext))

        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(sender, to, email_msg.as_string())
    except Exception:
        print('## Erro ao enviar email ##')
        print(f'* Assunto: {subject}')
        print(f'* Para: {to}')
        print(f'* Mensagem:\n{message}')
        return False
    finally:
        if server:
            server.quit()

    return True
