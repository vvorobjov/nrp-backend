#!/bin/bash

if [ -n "$ZSH_VERSION" ]; then
    PU_BASE=$(dirname $0)
    #setup completion for zsh
    compdef '_files -g *.py' run_pycodestyle
    compdef '_files -g *.py' run_pylint

elif [ -n "$BASH_VERSION" ]; then
    PU_BASE=$(dirname ${BASH_SOURCE[0]})
    #setup completion for bash
    complete -f -X '!*.py' run_pycodestyle
    complete -f -X '!*.py' run_pylint
fi

function echoerr() {
    echo "$@" 1>&2
}

function TRACE() {
    [[ -n $TRACE_UTILS ]] || echoerr "TRACE: $*"
}

function _handle_args() {
    TRACE "_handle_args: $*"
    while getopts ":c:o:" opt "$@"; do
        case "$opt" in
            c)
                CONFIG=$OPTARG
                ;;
            o)
                OUTPUT=$OPTARG
                ;;
        esac
    done
}

function _run_cmd() {
    TRACE "_run_cmd: $*"

    cmd=$1
    shift 1

    if [ -t 0 ]; then # if the input isn't a pipeline
        echo "$*" | xargs -r $cmd
    else
        xargs -r $cmd > $OUTPUT
    fi
}

#command to run pylint
function run_pylint () {
    TRACE "run_pylint"

    OUTPUT='pylint.txt'
    _handle_args "$@"
    shift $((OPTIND-1))

    #print version so we can debug
    pylint --version --rcfile=${CONFIG}

    PYLINT="pylint --rcfile=${CONFIG} -d I0011 -f parseable"

    _run_cmd "$PYLINT" $*
}

function run_pycodestyle () {
    TRACE "run_pycodestyle"

    OUTPUT='pycodestyle.txt'
    _handle_args "$@"
    shift $((OPTIND-1))

    #print version so we can debug
    echo "pycodestyle version: " $(pycodestyle --version)

    PYCODESTYLE="pycodestyle --config $CONFIG"
    _run_cmd "$PYCODESTYLE" $*
}

#only look at py files and not at doc, tests, or CI
function filter_python () {
    TRACE "filter_python"

    regex="doc/|tests|ContinuousIntegration/|jekylltest/"
    #filter out virtualenv files
    [[ -n $VIRTUAL_ENV ]] && regex="${regex}|$(basename "$VIRTUAL_ENV")"
    if [[ -n $1 ]]; then
        ignore="${1%|}" #strip trailing |
        regex="${regex}|${ignore#|}" #strip leading |, ensure that there is ONE |
    fi
    grep '\.py$' | egrep -v "$regex"
}

#vim:tabstop=4:softtabstop=4:shiftwidth=4
