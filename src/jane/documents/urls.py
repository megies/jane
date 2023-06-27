# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

from jane.documents import views, DOCUMENT_FILENAME_REGEX
from jane.jane.utils import OptionalTrailingSlashSimpleRouter

from .plugins import initialize_plugins  # NOQA


urlpatterns = [
    # Root url for the documents.
    url(r'^rest/documents/?$',
        view=views.documents_rest_root,
        name='rest_documents'),
    # Root url for the indices.
    url(r'^rest/document_indices/?$',
        view=views.documents_indices_rest_root,
        name='rest_documents_indices'),
    # Document data
    url(r'^rest/documents/(?P<document_type>[a-zA-Z0-9]+)'
        r'/(?P<name>' + DOCUMENT_FILENAME_REGEX + ')/data$',
        view=views.document_data,
        name='document_data'),
    # Attachment data
    url(r'^rest/document_indices/(?P<document_type>[a-zA-Z0-9]+)'
        r'/(?P<idx>[0-9]+)/attachments/(?P<pk>[0-9]+)/data$',
        view=views.attachment_data,
        name='attachment_data')

]
urlpatterns = format_suffix_patterns(urlpatterns)


# Route documents and document indices.
router = OptionalTrailingSlashSimpleRouter(trailing_slash=False)
router.register(prefix='documents/(?P<document_type>[a-zA-Z0-9]+)',
                viewset=views.DocumentsView,
                basename="rest_documents")
router.register(prefix='document_indices/(?P<document_type>[a-zA-Z0-9]+)',
                viewset=views.DocumentIndicesView,
                basename="rest_document_indices")
router.register(
    prefix=('document_indices/(?P<document_type>[a-zA-Z0-9]+)/(?P<idx>[0-9]+)'
            '/attachments'),
    viewset=views.DocumentIndexAttachmentsView,
    basename="rest_document_index_attachments")
urlpatterns.append(url(r'^rest/', include(router.urls)))


available_plugins = initialize_plugins()
