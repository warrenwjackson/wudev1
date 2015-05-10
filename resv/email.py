import sendgrid


def _get_email_list(seg):
    return ','.join(set([person.email for person in seg.get_persons()]))

def resv_confirm(resv):
    sg = sendgrid.SendGridClient('app21553765@heroku.com', 'fpnua0m5')
    for seg in resv.get_future_blocking_segs().filter(state='Confirmed'):
        message = sendgrid.Mail(to=_get_email_list(seg), subject='Confirmation #{0}'.format(seg.__unicode__()), html=seg.email_body(), text='Body')
        message.set_from('WU Resvervations <app21553765@heroku.com>')
        status, msg = sg.send(message)
        print 'sending email:'
        print status
        print msg