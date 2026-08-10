#!/usr/bin/env python3
# Copyright (c) 2026, Camptocamp SA

from c2cwsgiutils_app import models

from c2cwsgiutils.models_graph import generate_model_graph


def main():
    generate_model_graph(models)


main()
