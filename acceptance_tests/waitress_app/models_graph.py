#!/usr/bin/env python3
from c2cwsgiutils.models_graph import generate_model_graph

from c2cwsgiutils_app import models


def main():
    generate_model_graph(models)


main()
