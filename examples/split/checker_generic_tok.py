from __future__ import print_function, division, unicode_literals, absolute_import
from compgen.checkers import *


def get_sequence(file, exc=Exception):
    try:
        m = int(file.next())
        b = [int(file.next()) for i in xrange(m)]
    except Exception as e:
        raise ParseError("Failed to get a sequence: " + str(e))
    ensure(m >= 0, "Invalid length", exc=exc)
    return b

def check_valid(a, b, exc=Exception):
    # check subsequence
    j = 0
    for i in xrange(len(a)):
        if j < len(b) and a[i] == b[j]: j += 1
    ensure(j == len(b), "Not a subsequence!", exc=exc)
    # check distinct
    ensure(len(b) == len(set(b)), "Values not unique!", exc=exc)

@set_checker('tokens')
def check_solution(input_file, output_file, judge_file, **kwargs):
    z = int(input_file.next())
    for cas in xrange(z):
        n = int(input_file.next())
        ensure(n >= 1, "Judge data invalid!", exc=Fail)
        a = [int(input_file.next()) for i in xrange(n)]
        cont_b = get_sequence(output_file, exc=WA)
        judge_b = get_sequence(judge_file, exc=Fail)
        check_valid(a, cont_b, exc=WA)
        check_valid(a, judge_b, exc=Fail)
        if len(cont_b) < len(judge_b): raise WA("Suboptimal solution")
        if len(cont_b) > len(judge_b): raise Fail("Judge data incorrect!")

    if output_file.has_next(): raise WA("Extra characters at the end of the output file")
    if judge_file.has_next(): raise Fail("Extra characters at the end of the judge file!")
    return 1.0

if __name__ == '__main__': chk()
