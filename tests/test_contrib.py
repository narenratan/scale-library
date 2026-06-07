from scale_library.contrib import parse_details

def test_parse_details():
    scl_text = """! test.scl
This is the description
5
!
9/8
7/6
4/3
3/2
7/4
2/1
!
! This is the details text.
! It can be broken over several lines and
!
! It can contain multiple paragraphs
!
! [info]
! foo = bar
"""
    details = parse_details(scl_text)
    expected = """This is the details text.
It can be broken over several lines and

It can contain multiple paragraphs"""
    assert details == expected


def test_parse_details_2():
    scl_text = """! test.scl
This is the description
5
!
9/8
7/6
4/3
3/2
7/4
2/1
!
!
! [info]
! foo = bar
"""
    details = parse_details(scl_text)
    assert details == ""


def test_parse_details_3():
    scl_text = """! test.scl
This is the description
5
!
9/8
7/6
4/3
3/2
7/4
2/1
"""
    details = parse_details(scl_text)
    assert details == ""
