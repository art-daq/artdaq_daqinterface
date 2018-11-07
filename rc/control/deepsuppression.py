# JCF, 10/1/14
# I cut-and-pasted this from
# http://stackoverflow.com/questions/11130156/suppress-stdout-stderr-print-from-python-functions,
# as a tool to suppress unwanted output from compiled functions called
# within Python code (here, specifically, I'm referring to artdaq
# diagnostic output sent to stdout)
# Define a context manager to suppress stdout and stderr.

# JCF, Oct-19-2018

# deepsuppression's constructor now expects a boolean; deepsupression
# will simply be a no-op (i.e., the output it's meant to suppress will
# still go to stdout) only if the boolean is True. This makes it
# possible to control deepsuppression via DAQInterface's verbosity
# levels

import os


class deepsuppression(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).
    '''

    def __init__(self, activated=True):
        self.activated = activated
        if self.activated:
            # Open a pair of null files
            self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
            # Save the actual stdout (1) and stderr (2) file descriptors.
            self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        if self.activated:
            # Assign the null pointers to stdout and stderr.
            os.dup2(self.null_fds[0], 1)
            os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        if self.activated:
            # Re-assign the real stdout/stderr back to (1) and (2)
            os.dup2(self.save_fds[0], 1)
            os.dup2(self.save_fds[1], 2)
            # Close the null files
            os.close(self.null_fds[0])
            os.close(self.null_fds[1])

            # JCF, Sep-15-2018

            # The duplicates of the initial stdin and stdout also need to be closed...

            os.close(self.save_fds[0])
            os.close(self.save_fds[1])
