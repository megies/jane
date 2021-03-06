# -*- coding: utf-8 -*-
from rest_framework import status


class JaneException(Exception):
    """
    Base Jane exception.
    """
    pass


class JaneNotAuthorizedException(JaneException):
    """
    Exception raised when the current user is not authorized to perform a
    certain action.
    """
    status_code = status.HTTP_401_UNAUTHORIZED


class JaneDocumentAlreadyExists(JaneException):
    """
    Raised when a document already exists in the database.
    """
    status_code = status.HTTP_409_CONFLICT


class JaneInvalidRequestException(JaneException):
    """
    Raised when the request is invalid according to some special logic of Jane.
    """
    status_code = status.HTTP_400_BAD_REQUEST


class JaneWaveformTaskException(JaneException):
    """
    Exception raised during a waveform indexing task.
    """
    pass
