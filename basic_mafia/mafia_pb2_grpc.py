# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import mafia_pb2 as mafia__pb2


class MafiaServerStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ConnectClient = channel.unary_unary(
                '/mafia.MafiaServer/ConnectClient',
                request_serializer=mafia__pb2.ConnectRequest.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.ConnectToSpecificRoom = channel.unary_unary(
                '/mafia.MafiaServer/ConnectToSpecificRoom',
                request_serializer=mafia__pb2.ConnectToRoomRequest.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.EndDay = channel.unary_unary(
                '/mafia.MafiaServer/EndDay',
                request_serializer=mafia__pb2.Empty.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.VoteForMafia = channel.unary_unary(
                '/mafia.MafiaServer/VoteForMafia',
                request_serializer=mafia__pb2.Player.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.VoteToKill = channel.unary_unary(
                '/mafia.MafiaServer/VoteToKill',
                request_serializer=mafia__pb2.Player.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.CheckPlayer = channel.unary_unary(
                '/mafia.MafiaServer/CheckPlayer',
                request_serializer=mafia__pb2.Player.SerializeToString,
                response_deserializer=mafia__pb2.Response.FromString,
                )
        self.GetMessages = channel.unary_stream(
                '/mafia.MafiaServer/GetMessages',
                request_serializer=mafia__pb2.Empty.SerializeToString,
                response_deserializer=mafia__pb2.Message.FromString,
                )


class MafiaServerServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ConnectClient(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ConnectToSpecificRoom(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def EndDay(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def VoteForMafia(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def VoteToKill(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CheckPlayer(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetMessages(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MafiaServerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ConnectClient': grpc.unary_unary_rpc_method_handler(
                    servicer.ConnectClient,
                    request_deserializer=mafia__pb2.ConnectRequest.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'ConnectToSpecificRoom': grpc.unary_unary_rpc_method_handler(
                    servicer.ConnectToSpecificRoom,
                    request_deserializer=mafia__pb2.ConnectToRoomRequest.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'EndDay': grpc.unary_unary_rpc_method_handler(
                    servicer.EndDay,
                    request_deserializer=mafia__pb2.Empty.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'VoteForMafia': grpc.unary_unary_rpc_method_handler(
                    servicer.VoteForMafia,
                    request_deserializer=mafia__pb2.Player.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'VoteToKill': grpc.unary_unary_rpc_method_handler(
                    servicer.VoteToKill,
                    request_deserializer=mafia__pb2.Player.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'CheckPlayer': grpc.unary_unary_rpc_method_handler(
                    servicer.CheckPlayer,
                    request_deserializer=mafia__pb2.Player.FromString,
                    response_serializer=mafia__pb2.Response.SerializeToString,
            ),
            'GetMessages': grpc.unary_stream_rpc_method_handler(
                    servicer.GetMessages,
                    request_deserializer=mafia__pb2.Empty.FromString,
                    response_serializer=mafia__pb2.Message.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'mafia.MafiaServer', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class MafiaServer(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ConnectClient(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/ConnectClient',
            mafia__pb2.ConnectRequest.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def ConnectToSpecificRoom(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/ConnectToSpecificRoom',
            mafia__pb2.ConnectToRoomRequest.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def EndDay(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/EndDay',
            mafia__pb2.Empty.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def VoteForMafia(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/VoteForMafia',
            mafia__pb2.Player.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def VoteToKill(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/VoteToKill',
            mafia__pb2.Player.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def CheckPlayer(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaServer/CheckPlayer',
            mafia__pb2.Player.SerializeToString,
            mafia__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetMessages(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(request, target, '/mafia.MafiaServer/GetMessages',
            mafia__pb2.Empty.SerializeToString,
            mafia__pb2.Message.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
