from . import run_model


def test_my_stuff(benchmark):
    benchmark(run_model)
