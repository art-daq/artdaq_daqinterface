import zmq
import InhibitMaster

context = zmq.Context()
subscriber = InhibitMaster.InhibitSUBNode(context)
subscriber.connect("tcp://localhost:5566")

while True:
    msg = subscriber.recv_status_msg_timeout()
    print msg
