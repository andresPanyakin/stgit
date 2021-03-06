#!/bin/sh
# Copyright (c) 2006 Karl Hasselström
test_description='Test the mail command'
. ./test-lib.sh

test_expect_success \
    'Initialize the StGIT repository' \
    '
    for i in 1 2 3 4 5; do
      touch foo.txt &&
      echo "line $i" >> foo.txt &&
      stg add foo.txt &&
      git commit -a -m "Patch $i"
    done &&
    stg init &&
    stg uncommit -n 5 foo
    '

test_expect_success \
    'Put all the patches in an mbox' \
    '
    stg mail --to="Inge Ström <inge@example.com>" -a -m \
       -t $STG_ROOT/stgit/templates/patchmail.tmpl > mbox0 &&
    grep -e "From: .*author@example.com" mbox0 &&
    grep -e "To: .*inge@example.com" mbox0
    '

test_expect_success \
    'Use stgit.sender for sender' \
    '
    test_config stgit.sender "StGit Sender <stgit.sender@example.com" &&
    stg mail --to="Someone <someone@example.com>" -a -m \
       -t $STG_ROOT/stgit/templates/patchmail.tmpl > mbox0-sender &&
    grep -e "From: StGit Sender <stgit.sender@example.com>" mbox0-sender &&
    grep -e "To: Someone <someone@example.com>" mbox0-sender
    '

test_expect_success \
    'Use git user for sender' \
    '
    test_config user.name "Git User Name" &&
    test_config user.email "Git.User.Name@example.com" &&
    stg mail --to="Inge Ström <inge@example.com>" -a -m \
       -t $STG_ROOT/stgit/templates/patchmail.tmpl > mbox0-user &&
    grep -e "From: Git User Name <Git.User.Name@example.com>" mbox0-user &&
    grep -e "To: .*inge@example.com" mbox0-user
    '

test_expect_success \
    'No sender information' \
    '
    command_error test_env GIT_AUTHOR_NAME="" GIT_AUTHOR_EMAIL="" \
        stg mail --to="Inge Ström <inge@example.com>" -a -m \
        -t $STG_ROOT/stgit/templates/patchmail.tmpl 2>&1 >/dev/null |
    grep -e "Unknown sender name and e-mail"
    '

test_expect_success \
    'Import the mbox and compare' \
    '
    t1=$(git cat-file -p $(stg id) | grep ^tree)
    stg pop -a &&
    stg import -M mbox0 &&
    t2=$(git cat-file -p $(stg id) | grep ^tree) &&
    [ "$t1" = "$t2" ]
    '

test_expect_success \
    'Put all the patches in an mbox with patch attachments' \
    'stg mail --to="Inge Ström <inge@example.com>" --attach -a -m > mbox1'

test_expect_success \
    'Import the mbox containing patch attachments and compare' \
    '
    t1=$(git cat-file -p $(stg id) | grep ^tree)
    stg pop -a &&
    stg import -M mbox1 &&
    t2=$(git cat-file -p $(stg id) | grep ^tree) &&
    [ "$t1" = "$t2" ]
    '

test_expect_success 'Attach patches inline' '
    stg mail --to="Inge Ström <inge@example.com>" --attach-inline -a -m > mbox2
'

test_expect_success 'Import mbox containing inline attachments and compare' '
    t1=$(git cat-file -p $(stg id) | grep ^tree)
    stg pop -a &&
    stg import -M mbox1 &&
    t2=$(git cat-file -p $(stg id) | grep ^tree) &&
    [ "$t1" = "$t2" ]
    '

test_expect_success \
    'Check the To:, Cc: and Bcc: headers' \
    '
    stg mail --to=a@a --cc="b@b, c@c" --bcc=d@d $(stg top) -m > mbox &&
    test "$(cat mbox | grep -e "^To:")" = "To: a@a" &&
    test "$(cat mbox | grep -e "^Cc:")" = "Cc: b@b, c@c" &&
    test "$(cat mbox | grep -e "^Bcc:")" = "Bcc: d@d"
    '

test_expect_success \
    'Check the --auto option' \
    '
    stg edit --sign &&
    stg mail --to=a@a --cc="b@b, c@c" --bcc=d@d --auto $(stg top) -m > mbox &&
    test "$(cat mbox | grep -e "^To:")" = "To: a@a" &&
    grep -E "^Cc: (C =\?utf-8\?b\?w5M=\?= Mitter|=\?utf-8\?q\?C_=C3=93_Mitter\?=) <committer@example.com>, b@b, c@c$" mbox &&
    test "$(cat mbox | grep -e "^Bcc:")" = "Bcc: d@d"
    '

test_expect_success \
    'Check the e-mail address duplicates' \
    '
    stg mail --to="a@a, b b <b@b>" --cc="b@b, c@c" \
        --bcc="c@c, d@d, committer@example.com" --auto $(stg top) -m > mbox &&
    test "$(cat mbox | grep -e "^To:")" = "To: a@a, b b <b@b>" &&
    grep -E "^Cc: (C =\?utf-8\?b\?w5M=\?= Mitter|=\?utf-8\?q\?C_=C3=93_Mitter\?=) <committer@example.com>, c@c$" mbox &&
    test "$(cat mbox | grep -e "^Bcc:")" = "Bcc: d@d"
    '

test_expect_success 'Test no patches' '
    command_error stg mail
    '

test_expect_success 'Test no patches with --all' '
    stg pop -a &&
    command_error stg mail --all &&
    stg push
    '

test_expect_success 'Test empty patch' '
    stg new -m "empty" &&
    command_error stg mail empty &&
    stg clean
    '

test_expect_success 'Invalid --in-reply-to combinations' '
    echo "$(command_error stg mail --in-reply-to=xxx --no-thread $(stg top) 2>&1)" | \
        grep -e "in-reply-to option not allowed with" &&
    echo "$(command_error stg mail --in-reply-to=xxx --unrelated $(stg top) 2>&1)" | \
        grep -e "in-reply-to option not allowed with"
    '

test_expect_success 'Invalid --cover option combos' '
    echo "$(command_error stg mail --cover=cover.txt --unrelated $(stg top) 2>&1)" | \
        grep -e "cover sending not allowed with --unrelated" &&
    echo "$(command_error stg mail --edit-cover --unrelated $(stg top) 2>&1)" | \
        grep -e "cover sending not allowed with --unrelated"
    '

cat > cover.txt <<EOF
From: A U Thor <author@example.com>
Subject: Cover Test

A cover test.

EOF
test_expect_success 'User-specified cover file' '
    stg mail -m --cover=cover.txt $(stg top) > mbox-cover &&
    grep -e "Subject: Cover Test" mbox-cover &&
    grep -e "From: A U Thor" mbox-cover
    '

cat > editor <<EOF
#!/bin/sh
echo "Editor was invoked" | tee editor-invoked
EOF
chmod a+x editor
test_expect_success 'Edit cover' '
    EDITOR=./editor \
    stg mail -m --edit-cover $(stg top) | \
    grep -e "Subject: \[PATCH\] Series short description"
    '

test_done
