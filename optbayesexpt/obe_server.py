from .obe_socket import Socket
import numpy as np

class OBE_Server(Socket):
    """A TCP socket interface for OptBayesExpt using JSON strings

    This class provides communication between an OptBayesExpt object and
    user software running in a separate process. Instrumentation software is
    not always written in python; the idea of this class is to allow
    experiments to use OptBayesExpt from their native languages by issuing
    command messages in JSON :obj:`object` format through TCP sockets. The
    available commands are documented below in the ``run()`` method.

    Args:
        initial_args (:obj:`tuple`) Information needed for making OBE objects.
        ip_address(:obj:`str`): an IP address for TCP communications.
            Default '127.0.0.1'.
        port(:obj:`int`): a TCP port number to use for communications.
            Default 61981.

    Attributes:
        obe_engine (:obj:`OptBayesExpt`): The disembodied brains of the
            experimental design scheme. ``OBE_server`` provides TCP
            communication between ``obe_engine`` and a client program.
        initial_args (:obj:`tuple`): Stored samples from an
            initial parameter distribution.  Initialized by ``self.__init__()``
            and ``self.make_obe()``.

    Notes:
        1. The messages sent between the client and this server are expected
           to be JSON strings, each prependend by the string length formatted
           as a 10-digit number.  See the obe_socket module docs for
           details. Unless otherwise stated the server will reply with
           :code:`'0000000004"OK"'` upon successful completion of the command.

        2. The previous version of ``OBE_Server`` was a child class of
           ``OptBayesExpt``.  In this version, the ``OptBayesExpt`` is an
           attribute of ``OBE_Server``.  The advantage of the new
           arrangement is that OBE_Server can manage a sequence of
           experimental runs with differently configured
           ``OptBayesExpt`` objects.  See ``demos/magnetometer_demo.py`` and
           ``demos/magnetometer_server.py``.
    """

    def __init__(self, initial_args=(), ip_address='127.0.0.1', port=61981):

        Socket.__init__(self, 'server', ip_address=ip_address, port=port)

        self.initial_args = initial_args
        self.obe_engine = None

    def make_obe(self, obe_class, class_args):
        """Creates and attaches a new OptBayesExpt-like object

        A server may need to handle several runs. This function allows
        OBE_Server to instantiate new OptBayesExpt objects from scratch.
        Enables a server to start a new experimental run with modified
        starting conditions.

        Args:
            obe_class (:obj:`OptBayesExpt`-like) A class reference,
                e.g. ``optbayesexpt.OptBayesExpt`` without parentheses
            class_args (:obj:`tuple`): the arguments to the obe_class. For
                example, ``(model_function, settings, parameters, cons)``.
        """

        # save the arguments for possible reuse
        # these are owned by the OBE_Server instance as a "birth record"
        self.initial_args = class_args

        # create a new OptBayesExpt and attach it as the obe_engine attribute.
        self.obe_engine = obe_class(*class_args)

    def newrun(self, message):
        """A stub to allow customized TCP commands

        Invoked by the ``run`` method when a message with a ``'newrun'``
        command string is received. The idea is to provide flexible control
        from the experiment program. The original intent was to provide a
        way for the user program to start a fresh measurement, perhaps with
        different setting ranges or a different prior.  However, with access
        to the OBE_Server and its OptBayesExpt through the ``self``
        argument, and with any information the user chooses to send from the
        client program, there are many more possibilities.

        Args:
            self (:obj:`optbayesexpt.OBE_Server`):  provides access to the
                attributes of ``self`` and also its OptBayesExpt attribute.
            message (:obj:`tuple`): User defined information passed from the
                client program.

        Returns:  User defined.
        """
        pass

    def run(self):
        """Listens and responds to TCP messages

        Enters a continuous loop, interpreting incoming messages as python
        :obj:`dict` objects and responding to command strings found in
        ``message[ "command"]``.  Only one command string is allowed in each
        message. Valid command strings are listed below.

        **'done'**
            Stops the :code:`OBE_server` and allows the server script to
            complete.

                :code:`{"command": "done"}`

        Warning:

            It may be important for the client to issue the :code:`done`
            command. If the server is allowed to run, it will continue to
            use the TCP socket it was assigned during initialization.  Later
            instances of :code:`OBE_Server` may conflict.

        **'getcon'**
            Reports the :code:`OptBayesExpt.cons` attribute.  See also
            getset and getpar

                :code:`{"command": "getcon"}`

            Reply: a list of model constants.

        **'getcov'**
            Reports the covariance matrix of the parameter distribution as a
            JSON array of arrays.

                  :code:`{"command": "getcov"}`

            Reply: JSON formatted array of arrays

        **'getmean'**
            Reports the mean value of the parameter distribution as a JSON
            array.  See also getstd and getcov

                :code:`{"command": "getmean"}`

            Reply: JSON formatted array.

        **'getpar'**
            Reports the :code:`OptBayesExpt.parameters` arrays representing
            samples from the probability distribution.

                :code:`{"command": "getset"}`

            Reply: a list of parameter value lists.

        **'getset'**
            Reports the :code:`OptBayesExpt.sets` attribute

                :code:`{"command": "getset"}`

            Reply: a list of setting value lists.

        **'getstd'**
            Reports the standard deviation of the parameter distribution as
            a JSON array.

                :code:`{"command": "getstd"}`

            Reply: JSON formatted array

        **'getwgt'**
            Reports the particle weights of the probability distribution as
            a JSON array.

                :code:`{"command": "getwgt"}`

            Reply: particle weights as a JSON formatted array

        **'goodset'**
            Generated measurement settings. Calculates the utility of
            possible settings and reports a random selection that is
            weighted by the utility. Invokes
            :code:`OptBayesExpt.good_setting()`. See also optset.

                :code:`{"command": "goodset"[, "pickiness", <integer>]}`

            Reply: a list of setting values.

        **'newdat'**
            Processes measurement results. Refines the parameter probability
            distribution based on the *likelihood* of measurement results
            reported in the command. Invokes :code:`OptBayesExpt.pdf_update()`.

                :code:`{"command": "newdat", "x": <settings tuple>,
                "y": <measured values tuple>, "s": <uncertainty tuple>}`

            Required components include:

            * "x": a tuple containing the measurement settings.
            * "y": a tuple of measurement mean values.
            * "s": uncertainty of the measurement as a standard deviation.

        **'newrun'**
            A command string to run the user-defined
            :code:`OBE_Server.newrun()` method.  The message string must
            conform to the 10 digits + JSON object format, and it must avoid
            using other defined command strings.  Except for those
            restrictions, any ``<keyword>: <string>`` pairs are allowed.

                :code:`{"command": "newrun"[, ...]}`

            See the ``newrun()`` method documentation, above.

        **'optset'**
            Requests optimal measurement settings.  Calculates the utility
            of possible settings and reports the settings having the maximum
            utility. Invokes :code:`OptBayesExpt.opt_setting()`.  See also
            goodset.

                :code:`{"command": "optset"}`

            Reply: a list of setting values.

        """
        print()
        print('SERVER READY')
        while True:
            # use the Socket.receive() method to get the incoming message
            # from client
            message = self.receive()
            # the messages sent by the client are encoded as json objects
            # Decoded, by the ``receive``() method, they are python dicts.

            # These get* commands request arrays.  Numpy arrays must be
            # converted to lists
            if 'getset' in message['command']:
                self.send(np.array(self.obe_engine.allsettings).tolist())
            elif 'getpar' in message['command']:
                self.send(self.obe_engine.parameters.tolist())
            elif 'getcon' in message['command']:
                self.send(self.obe_engine.cons)
            elif 'getwgt' in message['command']:
                self.send(self.obe_engine.particle_weights.tolist())

            # run-time commands
            elif 'newrun' in message['command']:
                self.newrun(message)
                self.send('OK')

            elif 'optset' in message['command']:
                self.send(self.obe_engine.opt_setting())
            elif 'goodset' in message['command']:
                if 'pickiness' in list(message):
                    self.send(self.obe_engine.good_setting(
                        pickiness=message['pickiness']))
                else:
                    self.send(self.obe_engine.good_setting())

            elif 'newdat' in message['command']:
                self.obe_engine.pdf_update(
                    (message['x'], message['y'], message['s']))
                self.send('OK')

            # report statistics
            # Note: json.dumps() is not able to format numpy arrays.  To
            # send numpy arrays, the :code:`numpy.tolist()` is used to
            # list-ify a numpy arrays.
            elif 'getpdf' in message['command']:
                self.send(self.obe_engine.parameters.tolist())

            elif 'getwgt' in message['command']:
                self.send(self.obe_engine.particle_weights.tolist())

            elif 'getmean' in message['command']:
                mean = self.obe_engine.mean()
                self.send(mean.tolist())

            elif 'getstd' in message['command']:
                std = self.obe_engine.std()
                self.send(std.tolist())

            elif 'getcov' in message['command']:
                cov = self.obe_engine.covariance()
                self.send(cov.tolist())


            elif 'done' in message['command']:
                self.send('OK')
                break
            else:
                # the incoming message wasn't interpreted
                pass

    # end of run() method.
# end of OBE_Server definition
