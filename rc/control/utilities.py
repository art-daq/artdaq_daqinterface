
import os
import re

def expand_environment_variable_in_string(line):

    res = re.search(r"^(.*)(\$[A-Z]+)(.*)", line)

    if res:
        environ_var = res.group(2)
        environ_var = environ_var.strip("${}")

        if environ_var in os.environ.keys():
            line = res.group(1) + os.environ[ environ_var ] + res.group(3)
        else:
            raise Exception("Expanding line \"%s\", unable to find definition for environment variable \"%s\"" % \
                                (line.strip(), environ_var))

    return line
