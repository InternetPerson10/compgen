import io
import os.path
from html.parser import HTMLParser
from random import Random
from sys import stderr
from textwrap import dedent

script_path = os.path.dirname(os.path.realpath(__file__))

class PasswordException(Exception): ...

def create_passwords(cont, seedval=None):
    PASSWORD_LETTERS = 'ABCDEFGHJKLMNOPRSTUVWXYZ'
    VOWELS = set('AEIOUY')
    BLACKLIST = set('''
        yak yac pek pec ass fuc fuk fuq god gad omg not qum qoq qoc qok coq koq kik utn fux fck coc cok coq kox koc kok koq cac
        cak caq kac kak kaq pac bad lus pak ded dic die kil dik diq dix dck pns psy fag fgt ngr nig cnt knt sht dsh twt bch cum
        clt kum klt suc suk suq sck lic lik liq lck jiz jzz gay gey gei gai vag vgn sjv fap prn jew joo gvr pus pis pss snm tit
        fku fcu fqu hor slt jap wop kik kyk kyc kyq dyk dyq dyc kkk jyz prk prc prq mic mik miq myc myk myq guc guk guq giz gzz
        sex sxx sxi sxe sxy xxx wac wak waq wck pot thc vaj vjn nut std lsd poo azn pcp dmn orl anl ans muf mff phk phc phq xtc
        tok toc toq mlf rac rak raq rck sac sak saq pms nad ndz nds wtf sol sob fob sfu abu alh wag gag ggo pta pot tot put tut
        tet naz nzi xex cex shi xxi
    '''.upper().strip().split())

    accounts = [(key, account) for key in ['leaderboards', 'admins', 'judges', 'teams', 'feeders'] for account in getattr(cont, key)]
    if seedval is None:
        seedval = 0
        for idx, ch in enumerate(repr(tuple(accounts))):
            seedval = ((seedval * 123 + idx) * 22 + ord(ch)) % (10**6 + 3)

    print("Using seed {}".format(seedval), file=stderr)
    rand = Random(seedval)

    def make_chunk():
        while True:
            chunk = ''.join(rand.choice(PASSWORD_LETTERS) for i in range(3))
            if chunk in BLACKLIST: continue
            if set(chunk) & VOWELS: return chunk

    def make_password():
        return '-'.join(make_chunk() for i in range(4))

    return {account: make_password() for account in accounts}, seedval

def write_passwords(cont, format_, seedval=None, dest='.'):
    passwords, seedval = create_passwords(cont, seedval=seedval)

    if format_ == 'pc2':
        context = {
            'title': cont.title,
            'contest_code': cont.code,
            'seedval': seedval,
        }

        def get_rows():
            for row in [
                ('site', 'account', 'displayname', 'password', 'group', 'permdisplay', 'permlogin', 'externalid', 'alias', 'permpassword'),
            ]:
                yield row, None

            parser = HTMLParser()

            for idx, scoreboard in enumerate(cont.leaderboards, 1):
                display = scoreboard
                account = 'scoreboard{}'.format(idx)
                password = passwords['leaderboards', scoreboard]
                type_ = '[Scoreboard]'
                yield ('1', account, parser.unescape(display), password, '', 'false', 'true', str(1000 + idx), '', 'true'), (type_, display, account, password)

            for idx, admin in enumerate(cont.admins, 1):
                display = admin
                account = 'administrator{}'.format(idx)
                password = passwords['admins', admin]
                type_ = '[Administrator]'
                yield ('1', account, parser.unescape(display), password, '', 'false', 'true', str(1000 + idx), '', 'true'), (type_, display, account, password)

            for idx, judge in enumerate(cont.judges, 1):
                display = 'Judge ' + judge
                account = 'judge{}'.format(idx)
                password = passwords['judges', judge]
                type_ = '[Judge]'
                yield ('1', account, parser.unescape(display), password, '', 'false', 'true', str(1000 + idx), '', 'false'), (type_, display, account, password)

            for idx, feeder in enumerate(cont.feeders, 1):
                display = feeder
                account = 'feeder{}'.format(idx)
                password = passwords['feeders', feeder]
                type_ = '[Feeder]'
                yield ('1', account, parser.unescape(display), password, '', 'false', 'true', str(1000 + idx), '', 'true'), (type_, display, account, password)
            
            def team_schools():
                for ts in cont.team_schools:
                    for team in ts['teams']:
                        yield ts['school'], team

            for idx, (school_name, team_name) in enumerate(team_schools(), 1):
                display = team_name
                account = 'team{}'.format(idx)
                password = passwords['teams', team_name]
                type_= school_name
                yield ('1', account, parser.unescape(display), password, '', 'true', 'true', str(1000 + idx), '', 'false'), (type_, display, account, password)

        rows = []
        passrows = []
        for row, passrow in get_rows():
            rows.append(row)
            if passrow:
                passrows.append(passrow)

        contest_code = context['contest_code']

        filename = os.path.join(dest, 'accounts_{contest_code}.txt').format(**context)
        print("Writing to", filename, file=stderr)
        with io.open(filename, 'w', encoding='utf-8') as f:
            for row in rows:
                print(u'\t'.join(row), file=f)

        # TODO maybe use some jinja/django templating here...

        filename = os.path.join(dest, 'logins_{contest_code}_table.html').format(**context)
        print("Writing to", filename, file=stderr)
        with open(filename, 'w') as f:
            accounts = []
            for index, (university, display, login, password) in enumerate(passrows):
                accounts.append(dedent('''\
                    <tr class="pass-entry">
                    <td>{university}</td>
                    <td>{display}</td>
                    <td><code>{login}</code></td>
                    <td><code>{password}</code></td>
                    </tr>
                ''').format(
                    university=university,
                    display=display,
                    login=login,
                    password=password
                ))

            context['accounts'] = '\n'.join(accounts)
            with open(os.path.join(script_path, 'data', 'contest_template', 'pc2', 'logins_table.html')) as of:
                f.write(of.read().format(**context))

        filename = os.path.join(dest, 'logins_{contest_code}_boxes.html').format(**context)
        print("Writing to", filename, file=stderr)
        with open(filename, 'w') as f:
            accounts = []
            for index, (university, display, login, password) in enumerate(passrows):
                accounts.append(dedent('''\
                <strong>{display}</strong> <small><em>({contest_code})</em></small><br>
                <small>{university}</small>
                <table class="team-details table table-condensed table-bordered"><tbody>
                <tr><td>Login name</td><td><code>{login}</code></td></tr>
                <tr><td>Password</td><td><code>{password}</code></td></tr>
                </tbody></table>
                ''').format(
                    university=university,
                    display=display,
                    login=login,
                    password=password,
                    **context
                ))

            PER_ROW = 3
            account_rows = []
            row = []
            for account in accounts:
                row.append('<td style="width: %.6f%%">%s</td>' % (100. / PER_ROW, account))
                if len(row) == PER_ROW:
                    account_rows.append(row)
                    row = []
            if row:
                account_rows.append(row)

            context['accounts'] = '\n'.join('<tr>%s</tr>\n' % '\n'.join(row) for row in account_rows)
            with open(os.path.join(script_path, 'data', 'contest_template', 'pc2', 'logins_boxes.html')) as of:
                f.write(of.read().format(**context))
    else:
        raise PasswordException("Unsupported format: {}".format(format_))