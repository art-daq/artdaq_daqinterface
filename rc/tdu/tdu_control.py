import socket
import sys
import os
import errno
from rc.log import Logger
from time import sleep

class tdu_control:
    def __init__(self, HOST='pplxint8.physics.ox.ac.uk', PORT=50007, is_client=True, logpath=''):
        self.name    = 'tdu_control'
        #init the logger
        if logpath == '':
            logpath = os.path.join(os.environ["HOME"], ".tdu.log")
        self.logger = Logger(self.name, logpath)
        self.logger.log("%s starting!" % self.name)
        self.debug_level = 598 #high value = more debugging

        self.HOST = HOST  # The remote host
        self.PORT = PORT  # The same port as used by the server

        #the register location in memory
        self.REG_CONTROL = 0x0000
        self.REG_STATUS  = 0x0001
        self.REG_ERROR1  = 0x0014
        self.REG_ERROR2  = 0x000E

        #registers emulated
        self.REGS = [self.REG_CONTROL, self.REG_STATUS, self.REG_ERROR1, self.REG_ERROR2]

        #current value of the registers for the emulator
        self.VAL_CONTROL = 0x0000
        self.VAL_STATUS  = 0x0008
        self.VAL_ERROR1  = 0x0000
        self.VAL_ERROR2  = 0x0000
 
        #initialise to 0 so that we can't run as a server and a client simultaneously
        self.soc = 0

        #make connections
        if is_client:
            self.__connect_to_server()
        else:
            self.__start_listening()
            while 1:
                self.__accept_connection()
                self.__read_and_reply()
            self.__close_connection()


    def __print_log(self, printstr, debuglevel=999):
        self.logger.log(printstr)
        if self.debug_level <= debuglevel:
            print printstr

    #######################################
    # SERVER CONNECTION METHODS
    #######################################

    #Open up the socket & start listening
    def __start_listening(self):
        if self.soc != 0:
            print 'tdu_control::__start_listening()   Socket already exists. Cannot call both start_listening() and connect_to_server(). Exiting...'
            sys.exit(1)
        try:
            self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        except socket.error as msg:
            print 'tdu_control::__start_listening()   could not open socket'
            sys.exit(1)
        try:
            self.soc.bind(('', self.PORT))
            self.soc.listen(1)
        except socket.error as msg:
            self.soc.close()
            print 'tdu_control::__start_listening()   could not start listening on socket'
            sys.exit(1)

    #Accept a connection from a client
    def __accept_connection(self):
        self.conn, self.addr = self.soc.accept()
        print 'tdu_control::__accept_connection()   Connected by' + str(self.addr)

    #close
    def __close_connection(self):
        self.conn.close()


    #######################################
    # HOST CONNECTION METHODS
    #######################################

    #Open up the socket & connect to the server
    def __connect_to_server(self, socket_errors_are_fatal = False):
        if self.soc != 0:
            self.__print_log('tdu_control::__connect_to_server()   Socket already exists. Cannot call both start_listening() and connect_to_server(). Exiting...', 999)
            sys.exit(1)
        try:
            self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        except socket.error as msg:
            self.__print_log('tdu_control::__connect_to_server()   could not open socket', 999)
            if socket_errors_are_fatal:
                sys.exit(1)
            else:
                return msg
        try:
            self.soc.connect((self.HOST, self.PORT))
        except socket.error as msg:
            self.__print_log('tdu_control::__connect_to_server()   could not connect to the server', 999)
            if socket_errors_are_fatal:
                sys.exit(1)
            else:
                return msg

    #close
    def close_socket(self):
        try:
            self.soc.shutdown(socket.SHUT_RDWR)
            self.soc.close()
            return 0
        except socket.error as msg:
            self.__print_log('tdu_control::close_socket()   Could not close the socket', 999)
            return 600
            
    #try to connect to the server again, exit if this fails
    def reinit_client(self, ntries=10):
        self.__print_log('tdu_control::reinit_client()   Attempting to close_socket()', 999)
        self.close_socket()
        for i in xrange(1, ntries+1):
            self.__print_log('tdu_control::reinit_client()   Attempt ' + str(i) + ' of ' + str(ntries) + ' to __connect_to_server()', 999)
            self.soc = 0
            msg = self.__connect_to_server()
            if msg:
                sleep(10)
            else:
                self.__print_log('tdu_control::reinit_client()   Successfully reconnected to TDU', 999)
                return
        self.__print_log('FATAL tdu_control::reinit_client()   Could not reconnect to TDU', 999)
        sys.exit(1)

    #######################################
    # SERVER LOW-LEVEL COMMAND METHOD
    #######################################

    #Read requests & answer
    def __read_and_reply(self):
        while 1:
            data = self.conn.recv(1024)
            if not data:
                break
            #check the command is in the desired '$%02d*' format
            if data[0] != '$' or data[-1] != '*':
                break
            try:
                command = int(data[1:1+2])
            except ValueError:
                break
            if command < 1 or command > 17:
                break
            #get the register to read/write
            if command in [4,5]:
                register = int(data[4:4+6], 16)
            #get the data to write
            if command in [5]:
                wdata = int(data[11:11+6], 16)
                #write the data
                if register == self.REG_STATUS:
                    self.VAL_STATUS = wdata
                elif register == self.REG_CONTROL:
                    self.VAL_CONTROL = wdata
                    #also set the status register
                    if self.VAL_CONTROL != 0x0000:
                        self.VAL_STATUS = 0x8000
                    else:
                        self.VAL_STATUS = 0x0008
            #send the reply
            bytes_sent = 0
            #command 1 is ping
            #command 5 is write register
            if command in [1, 5]:
                bytes_sent = self.conn.send('*') #chr(int(0x2A))) # "*"
            #command 4 is read register
            elif command in [4]:
                if register not in self.REGS:
                    bytes_sent = self.conn.send('?') #chr(int(0x3F))) # "?"
                #STATUS REG
                if register == self.REG_STATUS:
                    bytes_sent = self.conn.send(self.__two_byte_hex_to_char_reverse(self.VAL_STATUS))
                    self.VAL_STATUS = 0x0008
                #CONTROL REG
                elif register == self.REG_CONTROL:
                    bytes_sent = self.conn.send(self.__two_byte_hex_to_char_reverse(self.VAL_CONTROL))
                #ERROR1 REG
                elif register == self.REG_ERROR1:
                    bytes_sent = self.conn.send(self.__two_byte_hex_to_char_reverse(self.VAL_ERROR1))
                #ERROR2 REG
                elif register == self.REG_ERROR2:
                    bytes_sent = self.conn.send(self.__two_byte_hex_to_char_reverse(self.VAL_ERROR2))                    
            else:
                bytes_sent = self.conn.send('?') #chr(int(0x3F))) # "?"
            print "tdu_control::__read_and_reply()   " + str(bytes_sent) + ' bytes sent'
        print "tdu_control::__read_and_reply()   Command received in incorrect format, or no data received"


    #######################################
    # HOST LOW-LEVEL COMMAND METHOD
    #######################################

    #send a $%02d[,REGISTER,DATA,]* command
    #and receive the reply
    def __send_command(self, i, reg='', data=''):
        #structure the command
        command = '${0:02d}'.format(i)
        if reg:
            command += ',' + reg
        if data:
            command += ',' + data
        if reg or data:
            command += ','
        command += '*'
        #send the command
        self.__print_log("tdu_control::__send_command()   Sending command: " + command, 299)
        bytes_sent = -1
        try:
            bytes_sent = self.soc.send(command)
        except socket.error as e:
            errnumber, errmsg = e
            if errnumber == errno.EPIPE:
                self.__print_log("tdu_control::__send_command()   Broken pipe on socket.send() - connection to TDU has been lost", 999)
            elif errnumber == errno.EBADF:
                self.__print_log("tdu_control::__send_command()   Bad file descriptor on socket.send() - connection to TDU has been lost", 999)
            else:
                self.__print_log("tdu_control::__send_command()   Exception on socket.send(): " + str(errnumber) + " " + errmsg, 999)
            self.reinit_client()
            return 140+i
        self.__print_log("tdu_control::__send_command()   " + str(bytes_sent) + " bytes sent", 199)
        #receive the reply
        reply = self.soc.recv(1024)
        if len(reply) == 0:
            self.__print_log("tdu_control::__send_command()   No reply received. Are you still connected to the TDU?", 999)
            return 120+i
        self.__print_log("tdu_control::__send_command()   Received " + str(len(reply)) + " byte(s):", 199)
        debug_reply = False
        if debug_reply:
            reply_bytes = ''
            for b in reply:
                reply_bytes += b + ' '
            self.__print_log("tdu_control::__send_command()   " + reply_bytes, 199)
        #check the reply for errors
        if i in [1,5]:
            if reply != '*':
                self.__print_log("tdu_control::__send_command()   Command failed (wrong number of bytes received)", 799)
                return 100+i
        elif i in [4, 12]:
            if len(reply) != 2:
                self.__print_log("tdu_control::__send_command()   Command failed (wrong number of bytes received)", 799)
                return 100+i
            reply_hex = self.__format_two_byte_received_data(reply)
            if reply_hex < 0:
                self.__print_log("tdu_control::__send_command()   Command failed (invalid register received)", 799)
                return reply_hex
            self.reply_hex = reply_hex
            self.__print_log("tdu_control::__send_command()   Received: " + self.__format_hex_as_string(reply_hex,4), 299)
        elif i in [2, 11]:
            if len(reply) != 13:
                self.__print_log("tdu_control::__send_command()   Command failed (wrong number of bytes received)", 799)
                return 100+i
        elif i in [3]:
            if len(reply) != 6:
                self.__print_log("tdu_control::__send_command()   Command failed (wrong number of bytes received)", 799)
                return 100+i
        self.reply = reply
        #return 0 unless the reply is wrong (number of bytes, or wrong range for a data read)
        return 0

    #######################################
    # HOST READ/WRITE METHODS
    #######################################

    #generic read register $04,REGISTER,* command
    def __send_read(self, reg):
        rstr = self.__format_two_byte_data_to_send(reg)
        if rstr < 0:
            return -rstr
        #return True unless the register is in the wrong format, or the reply is wrong
        return self.__send_command(4, rstr)

    #generic write register $05,REGISTER,DATA,* command
    def __send_write(self, reg, data):
        rstr = self.__format_two_byte_data_to_send(reg)
        #data is in the same format as the register
        dstr = self.__format_two_byte_data_to_send(data)
        if rstr < 0:
            return -rstr
        elif dstr < 0:
            return -dstr
        #return 0 unless the register is in the wrong format, or the reply is wrong
        return self.__send_command(5, rstr, dstr)


    #######################################
    # GENERIC STRING/CHAR TO HEX CONVERSION & VALIDITY METHODS
    #######################################

    #check the register is in a valid range & format
    def __valid_register(self, reg):
        try:
            reg_str = self.__two_byte_hex_to_char(reg)
        except:
            self.__print_log("tdu_control::__valid_register()   Register must be numerical in range 0x0000 to 0xFFFF", 899)
            return -200
        if reg < 0x0000 or reg > 0xFFFF:
            self.__print_log("tdu_control::__valid_register()   Register must be in range 0x0000 to 0xFFFF", 899)
            return -201
        return 0

    #slightly more human readable hex string (with leading zeros)
    def __format_hex_as_string(self, h, nzeros):
        return '0x' + hex(h)[2:].zfill(nzeros)

    def __format_char_as_string(self, c):
        return '0x' + format(ord(c), 'x').zfill(2)

    #convert hex number (max 0xFFFF) to 2 char string
    def __two_byte_hex_to_char(self, h):
        return "{0:c}{1:c}".format((h & 0xFF00) / 256, h & 0x00FF)

    #convert hex number (max 0xFFFF) to 2 char string, with bytes reversed
    def __two_byte_hex_to_char_reverse(self, h):
        return "{1:c}{0:c}".format((h & 0xFF00) / 256, h & 0x00FF)
 
    #convert a string of 8 char's to a hex number
    def __eight_byte_char_to_hex_reverse(self, s):
        return (ord(s[7]) * pow(2,56)) + (ord(s[6]) * pow(2,48)) + (ord(s[5]) * pow(2,40)) + (ord(s[4]) * pow(2,32)) + (ord(s[3]) * pow(2,24)) + (ord(s[2]) * pow(2,16)) + (ord(s[1]) * pow(2,8)) + ord(s[0])

    #convert a string of 4 char's to a hex number
    def __four_byte_char_to_hex_reverse(self, s):
        return (ord(s[3]) * pow(2,24)) + (ord(s[2]) * pow(2,16)) + (ord(s[1]) * pow(2,8)) + ord(s[0])

    #convert a string of 2 char's to a hex number
    def __two_byte_char_to_hex(self, s):
        return (ord(s[0]) * 256) + ord(s[1])

    #convert a string of 2 char's to a hex number, with bytes reversed
    def __two_byte_char_to_hex_reverse(self, s):
        return (ord(s[1]) * 256) + ord(s[0])

   #check the formatting of the register & convert it to a string
    def __format_two_byte_data_to_send(self, reg):
        valid = self.__valid_register(reg)
        if valid:
            return valid
        return self.__format_hex_as_string(reg, 4)

    #covert the string into a hex number
    def __format_two_byte_received_data(self, s):
        reg = self.__two_byte_char_to_hex_reverse(s)
        valid = self.__valid_register(reg)
        if valid:
            return valid
        else:
            return reg

    #######################################
    # HOST SPECIFIC COMMANDS
    #######################################

    ######### GET METHODS
    # return data along with an error code

    def get_status(self):
        #returns an int errorcode (0=sucessful read) & boolean ready_to_sync: [errcode, ready_to_sync]
        errcode = self.__send_read(self.REG_STATUS)
        if errcode:
            self.__print_log("tdu_control::get_status()   Read status failed", 699)
            return errcode, False
        not_ready_to_sync = self.reply_hex & 0x8000
        if not_ready_to_sync:
            self.__print_log("tdu_control::get_status()   Not ready to sync. Reason(s) below:", 599)
            if self.reply_hex & 0x0001:
                self.__print_log('tdu_control::get_status()   Calculating delay', 599)
            if self.reply_hex & 0x0004:
                self.__print_log('tdu_control::get_status()   Command busy', 599)
            if self.reply_hex & (~0x0008 & 0xFFFF):
                self.__print_log('tdu_control::get_status()   Not ready to sync', 599)
            if self.reply_hex & 0x0020:
                self.__print_log('tdu_control::get_status()   No command warning', 599)
            if self.reply_hex & 0x0080:
                self.__print_log('tdu_control::get_status()   Calculating NOvA timing', 599)
            if self.reply_hex & 0x0100:
                self.__print_log('tdu_control::get_status()   Scrubbing system', 599)
            return errcode, False
        if not (self.reply_hex & 0x0002):
            self.__print_log('tdu_control::get_status()   Delay not calculated (ever, or since last TDU reset)', 599)
        ready_to_sync     = self.reply_hex & 0x0008
        if ready_to_sync:
            self.__print_log("tdu_control::get_status()   Ready to sync", 599)
            return errcode, True
        self.__print_log("tdu_control::get_status()   Not ready to sync (reason unknown). Checking TDU & GPS status", 599)
        errcode = self.read_tdu_status()
        if errcode:
            self.__print_log("tdu_control::get_status()   TDU not ready", 599)
            return errcode, False
        errcode = self.read_gps_status()
        if errcode:
            self.__print_log("tdu_control::get_status()   GPS not ready", 599)
            return errcode, False
        self.__print_log("tdu_control::get_status()   I'm not ready to sync, and I've no idea why", 899)
        return errcode, False

    def get_nova_time(self, init_nova_time=False):
    #def get_nova_time_and_do_time_sync(self):
        #returns an int errcode (0=successful read) & int with the current 56-bit nova time (left-padded with 0) (-1 means fail)
        """
        #a time sync is required to update the 'NOvA time snapshot' registers
        errcode = self.do_time_sync()
        if errcode:
            self.__print_log("get_nova_time_and_do_time_sync()   Time synch failed. Cannot get current NOvA time", 699)
            return errcode, -1
        """
        if init_nova_time:
            errcode = self.debug_do_write_control_reg(0x0080)
            if errcode:
                self.__print_log("get_nova_time_and_do_time_sync()   Cannot update the current NOvA time", 699)
                return errcode, -1
            ready_to_sync = False
            while True:
                errcode, read_to_sync = self.get_status()
                if read_to_sync:
                    break
                sleep(1/32E6)
        ntime = 0
        errcode = self.__send_read(0x0050)
        if errcode:
            self.__print_log("get_nova_time_and_do_time_sync()   Could not read NOvA time snapshot register", 699)
            return errcode, -1
        ntime = ntime | (self.reply_hex << 48)
        errcode = self.__send_read(0x0051)
        if errcode:
            self.__print_log("get_nova_time_and_do_time_sync()   Could not read NOvA time snapshot register", 699)
            return errcode, -1
        ntime = ntime | (self.reply_hex << 32)
        errcode = self.__send_read(0x0052)
        if errcode:
            self.__print_log("get_nova_time_and_do_time_sync()   Could not read NOvA time snapshot register", 699)
            return errcode, -1
        ntime = ntime | (self.reply_hex << 16)
        errcode = self.__send_read(0x0053)
        if errcode:
            self.__print_log("get_nova_time_and_do_time_sync()   Could not read NOvA time snapshot register", 699)
            return errcode, -1
        ntime = ntime | (self.reply_hex)
        self.__print_log("get_nova_time_and_do_time_sync()   Current NOvA time is " + str(ntime), 599)
        return errcode, ntime

    ######### READ METHODS
    #return an error code only (results read to __print_log)

    def read_control_reg(self):
        #returns an int errorcode (0=sucessful read) & 2 byte hex (current value of register)
        self.__print_log("tdu_control::read_control_reg()   Retrieving control register value", 199)
        return self.__send_read(self.REG_CONTROL)

    def read_tdu_status(self):
        no_error = True
        errcode = self.__send_command(3)
        if errcode:
            return errcode
        s = self.reply
        self.__print_log('tdu_control::read_tdu_status()   TDU supply voltage: ' + str(self.__two_byte_char_to_hex_reverse(s[0:0+2]) * 0.00644), 599)
        self.__print_log('tdu_control::read_tdu_status()   TDU supply current: ' + str(((self.__two_byte_char_to_hex_reverse(s[2:2+2]) * 0.00322) / 50) / 0.033), 599)
        self.__print_log('tdu_control::read_tdu_status()   TDU temperature:    ' + str(self.__two_byte_char_to_hex_reverse(s[4:4+2]) * 0.0625), 599)
        fpga_status = ord(s[6])
        if fpga_status == 0x00:
            self.__print_log('tdu_control::read_tdu_status()   FPGA not booted', 599)
            no_error = False
        elif fpga_status == 0x01:
            self.__print_log('tdu_control::read_tdu_status()   FPGA booted', 599)
        else:
            self.__print_log('tdu_control::read_tdu_status()   FPGA status unknown ' + self.__format_hex_as_string(hex(fpga_status),2), 599)
            no_error = False
        fan_status = ord(s[7])
        if fan_status == 0x00:
            self.__print_log('tdu_control::read_tdu_status()   Fan normal', 599)
            no_error = False
        if fan_status == 0x01:
            self.__print_log('tdu_control::read_tdu_status()   Fan error', 599)
        else:
            self.__print_log('tdu_control::read_tdu_status()   Fan status unknown ' + self.__format_hex_as_string(hex(fan_status),2), 599)
            no_error = False
        if no_error:
            return 0
        return 301


    def read_gps_status(self):
        no_error = True
        errcode = self.__send_command(12)
        if errcode:
            return errcode
        h = self.reply_hex
        if not h & 0x0001:
            self.__print_log('tdu_control::read_gps_status()   GPS unit not present', 599)
            no_error = False
        fix_status = (h & 0x0006) >> 1
        def print_fix_status(fix_status):
            if fix_status == 0x01:
                self.__print_log('tdu_control::read_gps_status()   No GPS fix', 599)
                return False
            elif fix_status == 0x02:
                self.__print_log('tdu_control::read_gps_status()   2D GPS fix', 599)
                return True
            elif fix_status == 0x03:
                self.__print_log('tdu_control::read_gps_status()   3D GPS fix', 599)
                return True
            else:
                self.__print_log('tdu_control::read_gps_status()   GPS fix status unknown', 599)
                return False
        if not print_fix_status(fix_status):
            no_error = False
        if h & 0x0010:
            self.__print_log('tdu_control::read_gps_status()   No 1pps detected', 599)
            no_error = False
        if h & 0x0020:
            self.__print_log('tdu_control::read_gps_status()   Satellite lock lost', 599)
            no_error = False
        if h & 0x0040:
            self.__print_log('tdu_control::read_gps_status()   Unit in holdover mode (lock lost)', 599)
            no_error = False
        if h & 0x0080:
            self.__print_log('tdu_control::read_gps_status()   Antenna fault', 599)
            no_error = False
        self.__print_log('tdu_control::read_gps_status()   ' + str(int(h & 0x0F00)) + ' satellites locked', 599)
        
        no_error = True
        errcode = self.__send_command(11)
        if errcode:
            return errcode
        s = self.reply
        gps_timeout = ord(s[0])
        if gps_timeout == 0x00:
            pass
        elif gps_timeout == 0x01:
            self.__print_log('tdu_control::read_gps_status()   GPS timeout. No data sent for more than 5 seconds', 599)
            no_error = False
        else:
            self.__print_log('tdu_control::read_gps_status()   GPS timeout status unknown', 599)
            no_error = False
        self.__print_log('tdu_control::read_gps_status()   ' + str(ord(s[1])) + 'GPS timeouts have occurred', 599)
        self.__print_log('tdu_control::read_gps_status()   ' + str(ord(s[2])) + 'satellites locked', 599)
        if not print_fix_status(s[3]):
            no_error = False
        self.__print_log('tdu_control::read_gps_status()   UTC time HH:MM:ss' + str(ord(s[6])) + ':' + str(ord(s[5])) + ':' + str(ord(s[4])), 599)
        self.__print_log('tdu_control::read_gps_status()   GPS time of week'  + str(self.__four_byte_char_to_hex_reverse(s[7:7+4])), 599)
        self.__print_log('tdu_control::read_gps_status()   Current UTC week'  + str(self.__two_byte_char_to_hex_reverse(s[11:11+2])), 599)

        if no_error:
            return 0
        return 302


    def debug_read_all_registers(self):
        registers = []
        registers.append([0x0000, 'Control', ''])
        registers.append([0x0001, 'Status' , '0x0008 or 0x000A'])
        registers.append([0x0002, 'TDU delay value', ''])
        registers.append([0x0003, 'DCM delay value side', ''])
        registers.append([0x0004, 'DCM delay value top', ''])
        registers.append([0x0005, 'GPS time of week low', ''])
        registers.append([0x0006, 'GPS time of week high', ''])
        registers.append([0x0007, 'GPS week number', ''])
        registers.append([0x0008, 'Delay offset', ''])
        registers.append([0x0009, 'Control2', ''])
        registers.append([0x000A, '1pps verification low', ''])
        registers.append([0x000B, '1pps verification high', ''])
        registers.append([0x000C, 'Interrupt', ''])
        registers.append([0x000D, 'Early SYNC value', ''])
        registers.append([0x000E, 'Error2', '0x0000'])
        registers.append([0x000F, 'Error2 disable', '0x0000'])
        registers.append([0x0010, 'Preset time (bytes 1/0)', ''])
        registers.append([0x0011, 'Preset time (bytes 3/2)', ''])
        registers.append([0x0012, 'Preset time (bytes 5/4)', ''])
        registers.append([0x0013, 'Preset time (bytes 7/6)', ''])
        registers.append([0x0014, 'Error', '0x0000'])
        registers.append([0x0015, 'Firmware ID', ''])
        registers.append([0x0016, 'TDU type', ''])
        registers.append([0x0017, 'Event fifo overflow count', ''])
        registers.append([0x0019, 'Error disable', ''])
        registers.append([0x001A, 'pps width', ''])
        registers.append([0x001B, 'Event timestamp (bytes 1/0)', ''])
        registers.append([0x001C, 'Event timestamp (bytes 3/2)', ''])
        registers.append([0x001D, 'Event timestamp (bytes 5/4)', ''])
        registers.append([0x001E, 'Event timestamp (bytes 7/6)', ''])
        registers.append([0x001F, 'Event number', ''])
        registers.append([0x0020, 'Command data', ''])
        registers.append([0x0021, 'Command address', ''])
        registers.append([0x0022, 'Command header', ''])
        registers.append([0x0023, 'Event list mask', ''])
        registers.append([0x0024, 'Interrupt mask', ''])
        registers.append([0x0025, 'GPS lock lost counter', ''])
        registers.append([0x0026, 'GPS holdover counter', ''])
        registers.append([0x0027, 'GPS antenna fault counter', ''])
        registers.append([0x0028, 'GPS lock loss timer', ''])
        registers.append([0x0029, 'Event list mask2', ''])
        registers.append([0x0030, 'Command history timestamp (bytes 1/0)', ''])
        registers.append([0x0031, 'Command history timestamp (bytes 3/2)', ''])
        registers.append([0x0032, 'Command history timestamp (bytes 5/4)', ''])
        registers.append([0x0033, 'Command history timestamp (bytes 7/6)', ''])
        registers.append([0x0034, 'Command history data', ''])
        registers.append([0x0035, 'Command history address', ''])
        registers.append([0x0036, 'Command history header', ''])
        registers.append([0x0037, 'Command history word count', ''])
        registers.append([0x0040, 'Decoded time (bytes 1/0)', ''])
        registers.append([0x0041, 'Decoded time (bytes 3/2)', ''])
        registers.append([0x0042, 'Decoded time (bytes 5/4)', ''])
        registers.append([0x0043, 'Decoded time (bytes 7/6)', ''])
        registers.append([0x0050, 'NOvA time snapshot (bytes 1/0)', ''])
        registers.append([0x0051, 'NOvA time snapshot (bytes 3/2)', ''])
        registers.append([0x0052, 'NOvA time snapshot (bytes 5/4)', ''])
        registers.append([0x0053, 'NOvA time snapshot (bytes 7/6)', ''])

        colwidth = [10, 50, 10, 30]
        self.__print_log("tdu_control::debug_get_all_registers()   Retrieving value of all registers. Will return in format:\n" + "".join(word.ljust(colwidth[i]) for i, word in enumerate(['Location','Name','Value','Default'])))
        for reg in registers:
            loc, name, default = reg
            errcode = self.__send_read(loc)
            if errcode:
                return errcode
            self.__print_log("".join(word.ljust(colwidth[i]) for i, word in enumerate([self.__format_hex_as_string(loc,4), name, self.__format_hex_as_string(self.reply_hex,4), default])), 599)
            

    def read_error_registers(self):
        no_error = True
        errcode = self.__send_read(self.REG_ERROR1)
        if errcode:
            self.__print_log("tdu_control::read_error_registers()   Read error register failed", 799)
            return errcode
        if self.reply_hex & 0x0001:
            self.__print_log("tdu_control::read_error_registers()    No comma character seen in 1024 transfers", 799)
            no_error = False
        if self.reply_hex & 0x0002:
            self.__print_log("tdu_control::read_error_registers()    No SYNC echo", 799)
            no_error = False
        if self.reply_hex & 0x0004:
            self.__print_log("tdu_control::read_error_registers()    No timing link clock present", 799)
            no_error = False
        if self.reply_hex & 0x0008:
            self.__print_log("tdu_control::read_error_registers()    Checksum error", 799)
            no_error = False
        if self.reply_hex & 0x0010:
            self.__print_log("tdu_control::read_error_registers()    GPS 1pps not present", 799)
            no_error = False
        if self.reply_hex & 0x0020:
            self.__print_log("tdu_control::read_error_registers()    GPS lost satellite lock", 799)
            no_error = False
        if self.reply_hex & 0x0040:
            self.__print_log("tdu_control::read_error_registers()    GPS holdover active", 799)
            no_error = False
        if self.reply_hex & 0x0080:
            self.__print_log("tdu_control::read_error_registers()    GPS antennae fault", 799)
            no_error = False
        if self.reply_hex & 0x0100:
            self.__print_log("tdu_control::read_error_registers()    TCLK parity error", 799)
            no_error = False
        if self.reply_hex & 0x0400:
            self.__print_log("tdu_control::read_error_registers()    MIBS parity error", 799)
            no_error = False
        if self.reply_hex & 0x1000:
            self.__print_log("tdu_control::read_error_registers()    No value in offset register", 799)
            no_error = False
        if self.reply_hex & 0x2000:
            self.__print_log("tdu_control::read_error_registers()    No SYNC", 799)
            no_error = False
        if self.reply_hex & 0x4000:
            self.__print_log("tdu_control::read_error_registers()    SERDES error", 799)
            no_error = False
        if self.reply_hex & 0x8000:
            self.__print_log("tdu_control::read_error_registers()    Illegal register access", 799)
            no_error = False

        errcode = self.__send_read(self.REG_ERROR2)
        if errcode:
            self.__print_log("tdu_control::read_error_registers()   Read error register failed", 799)
            return errcode
        if self.reply_hex & 0x0001:
            self.__print_log("tdu_control::read_error_registers()    NMEA timeout", 799)
            no_error = False
        if self.reply_hex & 0x0002:
            self.__print_log("tdu_control::read_error_registers()    1pps accuracy test failure", 799)
            no_error = False
        if self.reply_hex & 0x0004:
            self.__print_log("tdu_control::read_error_registers()    Framing error", 799)
            no_error = False
        if self.reply_hex & 0x0008:
            self.__print_log("tdu_control::read_error_registers()    Dynamic GPS lost satellite lock", 799)
            no_error = False
        if self.reply_hex & 0x0010:
            self.__print_log("tdu_control::read_error_registers()    Time sync bit in control register stuck", 799)
            no_error = False

        if no_error:
            return 0
        else:
            return 400


    def read_tdu_id(self):
        errcode = self.__send_command(2)
        if errcode:
            return errcode
        s = self.reply
        self.__print_log('tdu_control::read_tdu_id()   TDU type:     ' + self.__format_char_as_string(s[0]), 599)
        self.__print_log('tdu_control::read_tdu_id()   TDU serial:   ' + str(hex(self.__eight_byte_char_to_hex_reverse(s[1:1+8]))), 599)
        self.__print_log('tdu_control::read_tdu_id()   SW version:   v' + self.__format_char_as_string(s[10]) + 'r' + self.__format_char_as_string(s[9]), 599)
        self.__print_log('tdu_control::read_tdu_id()   FPGA version: v' + self.__format_char_as_string(s[12]) + 'r' + self.__format_char_as_string(s[11]), 599)
        return 0


    ######### DO METHODS
    #actually make the TDU do something
    #returns an errorcode

    def debug_do_write_control_reg(self, data_to_or):
        #returns an int errorcode (0=success)
        maxattempts = 10
        for i in xrange(1, maxattempts+1):
            errcode, ready_to_sync = self.get_status()
            if errcode:
                self.__print_log("tdu_control::debug_do_write_control_reg()   Could not retrieve TDU status", 899)
                return errcode
            elif not ready_to_sync:
                if i < maxattempts:
                    self.__print_log("tdu_control::debug_do_write_control_reg()   Not ready to sync. Will wait 0.2 seconds & try again (attempt " + str(i) + " of " + str(maxattempts) + ")", 899)
                    sleep(0.2)
                else:
                    self.__print_log("tdu_control::debug_do_write_control_reg()   Not ready to sync. Giving up", 899)
                    return 300
            elif ready_to_sync:
                break
        errcode = self.read_control_reg()
        if errcode:
            self.__print_log("tdu_control::debug_do_write_control_reg()   Could not retrieve control register value", 899)
            return errcode
        return self.__send_write(self.REG_CONTROL, self.reply_hex | data_to_or)

    def do_ping(self):
        #returns an int errorcode (0=success)
        self.__print_log("tdu_control::do_ping()   Performing ping", 599)
        return self.__send_command(1)

    def do_time_sync(self):
        #returns an int errorcode (0=success)
        self.__print_log("tdu_control::do_time_sync()   Performing time synchronisation", 599)
        return self.debug_do_write_control_reg(0x0020)

    def do_delay_calc(self):
        #returns an int errorcode (0=success)
        self.__print_log("tdu_control::do_delay_calc()   Performing propagation delay calculation", 599)
        errcode = self.debug_do_write_control_reg(0x0010)
        if errcode:
            self.__print_log("tdu_control::do_delay_calc()   Could not start propagation delay calculation", 599)
            return errcode
        maxattempts = 10
        for i in xrange(1, maxattempts+1):
            sleep(10) #the delay calc takes a few seconds
            errcode, ready_to_sync = self.get_status()
            if (not errcode) and ready_to_sync:
                break
        if errcode:
            self.__print_log("tdu_control::do_delay_calc()   Could not get status after propagation delay calculation", 599)
            return errcode
        if not ready_to_sync:
            self.__print_log("tdu_control::do_delay_calc()   TDU status not returned to ready after 10*" + str(maxattempts) + "seconds. Is a loopback connector installed on all unused 'Timing out' RJ-45 connectors?", 899)
        errcode = self.__send_read(0x0002)
        if errcode:
            self.__print_log("tdu_control::do_delay_calc()   Could not get value of TDU delay", 599)
            return errcode
        self.__print_log("tdu_control::do_delay_calc()   Success! Delay value in this TDU is " + str(int(self.reply_hex)) + " usec", 599)
        return errcode

    def do_send_sync_pulse(self):
        #returns an int errorcode (0=success)
        self.__print_log("tdu_control::do_send_sync_pulse()   Sending sync pulse", 599)
        return self.debug_do_write_control_reg(0x0200)




