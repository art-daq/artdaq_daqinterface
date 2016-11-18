
def stop_datataking_base(self):
    
     try:
         self.attempt_lcm_pulse("stop")
     except:
         self.print_log("DAQInterface caught an exception " +
                        "in do_stop_running()")
         self.print_log(traceback.format_exc())

         self.print_log("%s, returned string is: " % (procinfo.name,))
         self.print_log(procinfo.lastreturned)

         self.alert_and_recover("An exception was "
                                "thrown during the stop transition")
         return
