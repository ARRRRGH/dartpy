import os
import shutil
import subprocess as sp
from joblib import Parallel, delayed
from subprocess import call
from functools import partial

import utils.general
import simulation.simulation as simul

class Runner(object):
    """
    Runner class creates schedules run executions.
    """
    def __init__(self, run_params, n_jobs=1, *args, **kwargs):
        self.run_params = run_params
        self.jobs = []
        self.n_jobs = n_jobs

        # TODO: check if simulation paths are up to date
        # TODO: merge run_params with run params in simulation.params then save simulation

    def _split_runner_in_jobs(self, *args, **kwargs):
        if type(self.run_params) is list:
            for runner in self.run_params:
                if type(runner) is list:
                    self.jobs.append(delayed(SequenceRunner(run_params=self.run_params, *args, **kwargs)).run)
                elif type(runner) is str:
                    self.jobs.append(delayed(SimulationRunner(runner).run)(*args, **kwargs))
                elif type(runner) is SimulationRunner:
                    self.jobs.append(delayed(runner.run)(*args, **kwargs))
                elif type(runner) is dict:
                    if 'sequence' in runner:
                        self.jobs.append(delayed(SequenceRunner(run_params=runner['sequence'], **runner).run))
                    if 'parallel' in runner:
                        self.jobs.append(delayed(SequenceRunner(run_params=runner['parallel'], **runner).run))
                else:
                    self.jobs.append(delayed(runner.run))
        else:
            raise Exception('run_params must be a list of simulations or paths to simulations or else valid' +
                            ' run_params dicts.')

    def run(self, *args, **kwargs):
        self._split_runner_in_jobs(*args, **kwargs)
        Parallel(n_jobs=self.n_jobs)(self.jobs)

    def _create_db(self, simulation):
        pass

    def _copy_maket(self, src_simulation, simulations):
        pass

    def _copy_dtm(self, src_simulation, simulations):
        pass

    def _restore_db(self):
        pass


class SequenceRunner(Runner):
    """
    A sequence runner preserves the order of run executions. There is no sharing of databases between two runs in a
    sequence. It deletes the created database after each run.
    """
    def __init__(self, keep_db=False, keep_maket=False, keep_dtm=False, *args, **kwargs):
        Runner.__init__(self, *args, **kwargs)
        self.keep_db = keep_db
        self.keep_maket = keep_maket
        self.keep_dtm = keep_dtm
        self.n_jobs = 1 # fix the number of jobs to assure sequential execution

    def _split_runner_in_jobs(self, *args, **kwargs):
        # while looping check that all elements are singular, nesting is not supported
        for i, runner in enumerate(self.run_params):
            if not type(runner) is str or type(runner) is SimulationRunner:
                raise Exception('run_params must be list of str or SimulationRunners')

            if type(runner) is str:
                runner = SimulationRunner(runner, *args, **kwargs)
            if i == 0:
                self.jobs.append(delayed(self._create_db)(runner.simulation))
                self.jobs.append(delayed(runner.run))
                if self.keep_maket:
                    self.jobs.append(delayed(self._copy_maket)(runner.simulation))
                if self.keep_dtm:
                    self.jobs.append(delayed(self._copy_dtm)(runner.simulation))
            else:
                if not self.keep_db:
                    self.jobs.append(delayed(self._create_db))
                self.jobs.append(delayed(runner.run)(*args, **kwargs))

        self.jobs.append(delayed(self._restore_db))

class ParallelRunner(Runner):
    """
    A parallel runner runs dart in parallel. As long as I don't know whether there is a possibility to add external
    databases, use of a parallel runner assumes that simulations in it rely on the same databases.
    """
    def __init__(self, keep_maket=False, keep_dtm=False, *args, **kwargs):
        Runner.__init__(self, *args, **kwargs)
        self.keep_maket = keep_maket
        self.keep_dtm = keep_dtm

        runner = self.run_params[0]
        if runner is str:
            runner = SimulationRunner(runner)

        self._create_db(runner.simulation)
        runner.run(prepare=True)

        if self.keep_maket:
            self._copy_maket(runner.simulation)
        if self.keep_dtm:
            self._copy_dtm(runner.simulation)

        self.jobs.append(delayed(runner.complete)(*args, **kwargs))

    def _split_runner_in_jobs(self, *args, **kwargs):
        # while looping check that all elements are singular, nesting is not supported
        if len(self.run_params) > 1:
            for i, runner in enumerate(self.run_params[1:]):
                if not type(runner) is str or type(runner) is SimulationRunner:
                    raise Exception('run_params must be list of str or SimulationRunners')

                if type(runner) is str:
                    runner = SimulationRunner(runner, *args, **kwargs)
                self.jobs.append(delayed(runner.run)(*args, **kwargs))

        self.jobs.append(delayed(self._restore_db))


class SimulationRunner(object):
    """
    Class dispatching and handling the run of a single simulation.
    """

    def __init__(self, simulation, *args, **kwargs):
        self.simulation = simulation

    def run(self, prepare=True, *args, **kwargs):
        self.prepare(self.simulation)
        if not prepare:
            self.complete(self.simulation)

    def prepare(self, simulation, dart_path=None, *args, **kwargs):
        # check if simulation is in right place, if not copy if copy_if_external=True
        if dart_path is None:
            self.dart_path = simulation.params.get('dart_path')

        if dart_path is None:
            raise Exception('No valid dart_path is set.')

        sim_loc = utils.general.create_path(dart_path, 'user_data' 'simulations')

        fold, sim_name = os.path.split(simulation.path)
        sim_path = os.path.abspath(utils.general.create_path(sim_loc, sim_name))

        # TODO: does folder *really* need to be in DART directory?
        does_sim_name_exist = os.path.exists(sim_path)
        if not simulation.path.startswith(os.path.abspath(dart_path)):
            if not does_sim_name_exist:
                shutil.copytree(simulation.simulation_location, sim_path)
                # Update simulation params
                simulation.path = sim_path
            else:
                raise Exception('Simulation with the name ' + simulation.name +
                                ' does already exist in simulation directory.')

        self._dart_prep_runs(simulation, dart_path, *args, **kwargs)

    def complete(self, *args, **kwargs):
        fold, simulation_name = os.path.split(self.simulation.path)
        self._run_dart_only(simulation_name, self.dart_path, *args, **kwargs)

    def _dart_prep_runs(self, simulation, dart_path, *args, **kwargs):
        fold, simulation_name = os.path.split(simulation.path)

        # TODO: find out if order matters, if not run this multithreaded
        self._run_dem(simulation_name, dart_path, simulation, *args, **kwargs)
        self._run_direction(simulation_name, dart_path, *args, **kwargs)
        self._run_phase(simulation_name, dart_path, *args, **kwargs)
        self._run_maket(simulation_name, dart_path, simulation, *args, **kwargs)
        self._run_atmosphere(simulation_name, dart_path, *args, **kwargs)

    def _dart_run(self, simulation, dart_path, n_prep_threads=4, *args, **kwargs):
        fold, simulation_name = os.path.split(simulation.path)
        self._dart_prep_runs(simulation, dart_path, *args, **kwargs)
        self._run_dart_only(simulation_name, dart_path, *args, **kwargs)

    def _update_db(self, simulation, update_atmosphere_hook=None, update_lambertian_hook=None,
                   update_vegetation_hook=None):
        if update_atmosphere_hook is not None:
            update_atmosphere_hook(simulation)

        if update_lambertian_hook is not None:
            update_lambertian_hook(simulation)

        if update_vegetation_hook is not None:
            update_vegetation_hook(simulation)

    def _run_dem(self, simulation_name, dart_path, simulation, create_dtm_hook=None, shell=True):
        if create_dtm_hook is not None:
            create_dtm_hook(simulation)
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-dem-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_direction(self, simulation_name, dart_path, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-directions.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_maket(self, simulation_name, dart_path, simulation, adapt_maket_hook=None, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-maket-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        if adapt_maket_hook is not None:
            maket_path = utils.general.create_path(dart_path, 'output', 'maket.txt')
            adapt_maket_hook(simulation, maket_path)
        return p.communicate()

    def _run_phase(self, simulation_name, dart_path, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-phase-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_atmosphere(self, simulation_name, dart_path, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-atmosphere-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_dart_only(self, simulation_name, dart_path, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-only.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _adapt_maket(self, simulation):
        raise NotImplementedError

    def _create_dtm(self, simulation):
        raise NotImplementedError



