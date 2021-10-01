:orphan:

.. currentmodule:: appcommands
.. _faq:

Frequently Asked Questions
===========================

This is a list of Frequently Asked Questions regarding using ``dpy-appcommands``. Feel free to suggest a
new question or submit one via pull requests.

.. contents:: Questions
    :local:

General
--------

How do i make a Bot?
~~~~~~~~~~~~~~~~~~~~~

The simple answer is to use :class:`.Bot` class

Quick example: ::
    import appcommands

    bot = appcommands.Bot(command_prefix="$")
