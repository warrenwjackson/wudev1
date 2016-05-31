import sendgrid


def _get_email_list(seg):
    return ','.join(set([person.email for person in seg.get_persons()]))
def _client():
    return sendgrid.SendGridClient('app21553765@heroku.com', '8trlvbxa6734')
def send_email(to, subject, html):
    sg =  _client()
    message = sendgrid.Mail(to=to, subject=subject, html=html, text='Body')
    message.set_from('WU Resvervations <app21553765@heroku.com>')
    status, msg = sg.send(message)
    print 'sending email:', to, subject, html
   # print 'status', status
   # print msg   

def resv_confirm(resv):
    for seg in resv.get_future_blocking_segs().filter(state='Confirmed'):
        to = _get_email_list(seg)
        subject='Confirmation #{0}'.format(seg.__unicode__()) 
        html=seg.email_body()
        send_email(to, subject,html)

def standby_notification(seg):
    print 'standby_notification called'
    to = _get_email_list(seg)
    subject = "ACTION NEEDED: Standby available"
    html = "Click here to view details of your standby: http://127.0.0.1:8000/standby/choice/{0}".format(seg.id)
    send_email(to, subject, html)