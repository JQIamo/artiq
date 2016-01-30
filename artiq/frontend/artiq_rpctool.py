#!/usr/bin/env python3

import argparse
import textwrap
import sys
import numpy as np  # Needed to use numpy in RPC call arguments on cmd line
import pprint

from artiq.protocols.pc_rpc import Client

import json

def kwdict(string):
    return json.loads(string)

def get_argparser():
    parser = argparse.ArgumentParser(
        description="ARTIQ RPC tool")
    parser.add_argument("server",
                        help="hostname or IP of the controller to connect to")
    parser.add_argument("port", type=int,
                        help="TCP port to use to connect to the controller")
    subparsers = parser.add_subparsers(dest="action")
    subparsers.required = True
    subparsers.add_parser("list-targets", help="list existing targets")
    parser_list_methods = subparsers.add_parser("list-methods",
                                                help="list target's methods")
    parser_list_methods.add_argument("-t", "--target", help="target name")
    parser_call = subparsers.add_parser("call", help="call a target's method")
    parser_call.add_argument("-t", "--target", help="target name")
    parser_call.add_argument("-k", "--kwargs", help = "keyword arguments", type=kwdict)
    parser_call.add_argument("method", help="method name")

    parser_call.add_argument("args", nargs=argparse.REMAINDER,
                             help="arguments")
    return parser



def list_targets(target_names, description):
    print("Target(s):   " + ", ".join(target_names))
    if description is not None:
        print("Description: " + description)


def list_methods(remote):
    doc = remote.get_rpc_method_list()
    if doc.get("docstring", None) is not None:
        print(doc["docstring"])
        print()
    for name, (argspec, docstring) in sorted(doc.get("methods", {}).items()):
        args = ""
        for arg in argspec["args"]:
            args += arg
            if argspec.get("defaults", None) is not None:
                kword_index = len(argspec["defaults"]) - len(argspec["args"])\
                    + argspec["args"].index(arg)
                if kword_index >= 0:
                    if argspec["defaults"][kword_index] == Ellipsis:
                        args += "=..."
                    else:
                        args += "={}".format(argspec["defaults"][kword_index])
            if argspec["args"].index(arg) < len(argspec["args"]) - 1:
                args += ", "
        if argspec.get("varargs", None) is not None:
            args += ", *{}".format(argspec["varargs"])
        elif len(argspec.get("kwonlyargs",[])) > 0:
                args += ", *"
        for kwonlyarg in argspec.get("kwonlyargs", []):
            args += ", {}".format(kwonlyarg)
            if kwonlyarg in argspec.get("kwonlydefaults", []):
                if argspec["kwonlydefaults"][kwonlyarg] == Ellipsis:
                    args += "=..."
                else:
                    args += "={}".format(argspec["kwonlydefaults"][kwonlyarg])
        if argspec.get("varkw", None) is not None:
            args += ", **{}".format(argspec["varkw"])
        print("{}({})".format(name, args))
        if docstring is not None:
            print(textwrap.indent(docstring, "    "))
        print()


def call_method(remote, method_name, args, kwargs):
    method = getattr(remote, method_name)
    ret = method(*[eval(arg) for arg in args], **kwargs)
    if ret is not None:
        pprint.pprint(ret)


def main():
    args = get_argparser().parse_args()

    remote = Client(args.server, args.port, None)

    targets, description = remote.get_rpc_id()

    if args.action != "list-targets":
        # If no target specified and remote has only one, then use this one.
        # Exit otherwise.
        if len(targets) > 1 and args.target is None:
            print("Remote server has several targets, please supply one with "
                  "-t")
            sys.exit(1)
        elif args.target is None:
            args.target = targets[0]
        remote.select_rpc_target(args.target)

    if args.action == "list-targets":
        list_targets(targets, description)
    elif args.action == "list-methods":
        list_methods(remote)
    elif args.action == "call":
        print(args.args)
        print(args.kwargs)
        if args.kwargs is None:
            args.kwargs = {}
        call_method(remote, args.method, args.args, args.kwargs)
    else:
        print("Unrecognized action: {}".format(args.action))

if __name__ == "__main__":
    main()
