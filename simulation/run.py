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
    Runner class schedules run executions.
    """
    def __init__(self, runs, n_jobs=1, seq=False, db_update=None, update_atmosphere_hook=None,
                 update_lambertian_hook=None, create_dtm_hook=None, update_vegetation_hook=None, *args, **kwargs):

        self.update_atmosphere_hook = update_atmosphere_hook
        self.update_lambertian_hook = update_lambertian_hook
        self.update_vegetation_hook = update_vegetation_hook

        self.runs = runs
        self.jobs = []
        self.n_jobs = n_jobs
        if seq:
            self.n_jobs = 1

        self.db_update = db_update

        # TODO: check if simulation paths are up to date
        # TODO: merge runs with run params in simulation.params then save simulation

    def _create_jobs(self, *args, **kwargs):
        if type(self.runs) is list:
            for runner in self.runs:
                if type(runner) is list:
                    self.jobs.append(delayed(RunEnvironment(runs=self.runs, seq=True, *args, **kwargs)).run)
                elif type(runner) is str:
                    self.jobs.append(delayed(SimulationRunner(runner).run)(*args, **kwargs))
                elif type(runner) is SimulationRunner:
                    self.jobs.append(delayed(runner.run)(*args, **kwargs))
                elif type(runner) is dict:
                    if 'runs' in runner:
                        self.jobs.append(delayed(RunEnvironment(runs=runner['sequence'], **runner).run))
                else:
                    self.jobs.append(delayed(runner.run))
        else:
            raise Exception('runs must be a list of simulations or paths to simulations or else valid' +
                            ' runs dicts.')

    def run(self, *args, **kwargs):
        self._create_jobs(*args, **kwargs)
        Parallel(n_jobs=self.n_jobs)(self.jobs)


class RunEnvironment(Runner):
    """
    A run environment can load the needed databases and run simulations in with these databases either sequentially or
    in parallel.
    """
    def __init__(self, keep_maket=False, keep_dtm=False, *args, **kwargs):
        Runner.__init__(self, *args, **kwargs)
        self.keep_maket = keep_maket
        self.keep_dtm = keep_dtm

        runner = self.runs[0]
        if runner is str:
            runner = SimulationRunner(runner)

        self._create_db(runner.simulation)
        runner.run(only_prepare=True)

        if self.keep_maket:
            self._copy_maket(runner.simulation)
        if self.keep_dtm:
            self._copy_dtm(runner.simulation)

        self.jobs.append(delayed(runner.complete)(*args, **kwargs))

    def _create_jobs(self, *args, **kwargs):
        if len(self.runs) > 1:
            # check that all elements are singular, nesting is not supported
            for i, runner in enumerate(self.runs[1:]):
                if not type(runner) is str or type(runner) is SimulationRunner:
                    raise Exception('runs must be list of str or SimulationRunners')

                if type(runner) is str:
                    runner = SimulationRunner(runner, *args, **kwargs)
                self.jobs.append(delayed(runner.run)(*args, **kwargs))

        self.jobs.append(delayed(self._restore_db))

    def _create_db(self, simulation):
        if self.db_update is None:
            # TODO: mutlithreading?
            # copy existing db to safe place

            # apply hooks
            if self.update_atmosphere_hook is not None:
                self.update_atmosphere_hook(simulation)

            if self.update_vegetation_hook is not None:
                self.update_atmosphere_hook(simulation)

            if self.update_lambertian_hook is not None:
                self.update_atmosphere_hook(simulation)

    def _copy_maket(self, src_simulation, simulations):
        pass

    def _copy_dtm(self, src_simulation, simulations):
        pass

    def _restore_db(self):
        pass


class SimulationRunner(object):
    """
    Class dispatching and handling the run of a single simulation.
    """

    def __init__(self, simulation, pre_dem_hook=None, post_maket_hook=None, create_dtm_hook=None,
                 *args, **kwargs):

        self.simulation = simulation

        self.create_dtm_hook = create_dtm_hook
        self.post_maket_hook = post_maket_hook
        
        self.working_dir = None
        self.simulation_name = None

    def run(self, only_prepare=False, *args, **kwargs):
        self.prepare(self.simulation)
        if not only_prepare:
            self.complete(self.simulation)

    def prepare(self, simulation, dart_path=None, *args, **kwargs):
        # check if simulation is in right place, if not copy if copy_if_external=True
        if dart_path is None:
            self.dart_path = simulation.params.get('dart_path')

        if dart_path is None:
            raise Exception('No valid dart_path is set.')

        sim_loc = utils.general.create_path(dart_path, 'user_data' 'simulations')

        fold, self.simulation_name = os.path.split(simulation.path)
        self.working_dir = os.path.abspath(utils.general.create_path(sim_loc, self.simulation_name))

        # TODO: does folder *really* need to be in DART directory?
        does_sim_name_exist = os.path.exists(self.working_dir)
        if not simulation.path.startswith(os.path.abspath(dart_path)):
            if not does_sim_name_exist:
                shutil.copytree(simulation.path, self.working_dir)
                # Update simulation params
                self.working_dir = self.working_dir
            else:
                raise Exception('Simulation with the name ' + self.simulation_name +
                                ' does already exist in simulation directory.')
        else:
            self.working_dir = simulation.path

        self._dart_prep_runs(simulation, dart_path, *args, **kwargs)

    def complete(self, *args, **kwargs):
        self._run_dart_only(self.simulation_name, self.dart_path, *args, **kwargs)

    def _dart_prep_runs(self, simulation, dart_path, *args, **kwargs):
        # TODO: find out if order matters, if not run this multithreaded
        self._run_dem(self.simulation_name, dart_path, simulation, *args, **kwargs)
        self._run_direction(self.simulation_name, dart_path, *args, **kwargs)
        self._run_phase(self.simulation_name, dart_path, *args, **kwargs)
        self._run_maket(self.simulation_name, dart_path, simulation, *args, **kwargs)
        self._run_atmosphere(self.simulation_name, dart_path, *args, **kwargs)

    def _dart_run(self, simulation, dart_path, n_prep_threads=4, *args, **kwargs):
        self._dart_prep_runs(simulation, dart_path, *args, **kwargs)
        self._run_dart_only(self.simulation_name, dart_path, *args, **kwargs)

    def _run_dem(self, simulation_name, dart_path, simulation, shell=True):
        if self.create_dtm_hook is not None:
            self.create_dtm_hook(simulation)
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-dem-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_direction(self, simulation_name, dart_path, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-directions.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_maket(self, simulation_name, dart_path, simulation, shell=True):
        cmd = utils.general.create_path(dart_path, 'tools/linux/dart-maket-edit.sh') + ' ' + simulation_name
        p = sp.Popen(cmd, shell=shell)
        if self.post_maket_hook is not None:
            out_path = utils.general.create_path(dart_path, 'output')
            self.post_maket_hook(simulation, out_path)
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



