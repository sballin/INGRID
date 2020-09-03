import numpy as np
import matplotlib
import pathlib
import inspect
import yaml as yml
try:
    matplotlib.use("TkAgg")
except:
    pass
import matplotlib.pyplot as plt
from collections import OrderedDict


class Topology():
    def __init__(self, Ingrid_obj, config):
        self.parent = Ingrid_obj
        self.config = config
        self.settings = Ingrid_obj.settings
        self.PlateData = Ingrid_obj.PlateData
        self.PatchTagMap = self.parent.GetPatchTagMap(config=config)
        self.LineTracer = Ingrid_obj.LineTracer
        self.PsiUNorm = Ingrid_obj.PsiUNorm
        self.PsiNorm = Ingrid_obj.PsiNorm
        self.LineTracer = Ingrid_obj.LineTracer
        self.CurrentListPatch = {}
        self.ConnexionMap = {}
        self.Verbose = False
        self.PlateData = Ingrid_obj.PlateData
        self.GetCorrectDistortionSettings()

    def RefreshSettings(self):
        self.settings = self.parent.settings

    def OrderPatches(self):
        pass

    def patch_diagram(self, fig=None, ax=None):
        """
        Generates the patch diagram for a given configuration.
        @author: watkins35, garcia299
        """

        colors = {'A': 'red', 'B': 'blue', 'C': 'navajowhite', 'D': 'firebrick',
                  'E': 'magenta', 'F': 'olivedrab', 'G': 'darkorange', 'H': 'yellow', 'I': 'navy'}
        alpha = {'3': 1.0, '2': 0.75, '1': 0.5}

        f = fig if fig else plt.figure('INGRID Patch Map', figsize=(6, 10))
        a = ax if ax else f.subplots(1, 1)
        a.set_xlim([self.PsiUNorm.rmin, self.PsiUNorm.rmax])
        a.set_ylim([self.PsiUNorm.zmin, self.PsiUNorm.zmax])
        a.set_aspect('equal', adjustable='box')

        a.set_xlabel('R')
        a.set_ylabel('Z')
        a.set_title(f'{self.config} Patch Diagram')

        for i, patch in enumerate(self.patches.values()):
            patch.plot_border(color='black', ax=a)
            patch.fill(colors[patch.get_tag()[0]], ax=a, alpha=alpha[patch.get_tag()[-1]])
            patch.color = colors[patch.get_tag()[0]]
        # ax.legend()
        f.show()

    def grid_diagram(self, fig=None, ax=None):
        """
        Create Grid matplotlib figure for an SNL object.
        @author: watkins35, garcia299
        """
        if fig is None:
            fig = plt.figure('INGRID Grid', figsize=(6, 10))

        if ax is None:
            ax = fig.gca()

        ax.set_xlim(self.PsiUNorm.rmin, self.PsiUNorm.rmax)
        ax.set_ylim(self.PsiUNorm.zmin, self.PsiUNorm.zmax)
        ax.set_aspect('equal', adjustable='box')

        ax.set_xlabel('R')
        ax.set_ylabel('Z')
        ax.set_title(f'{self.config} Subgrid')

        for patch in self.patches.values():
            patch.plot_subgrid(ax=ax)
            print(f'# Plotting subgrid {patch.patchName}')

        fig.show()

    def animate_grid(self):

        try:
            plt.close('INGRID: Debug')
        except:
            pass
        plt.figure('INGRID: Debug', figsize=(6, 10))
        plt.xlim(self.PsiUNorm.rmin, self.PsiUNorm.rmax)
        plt.ylim(self.PsiUNorm.zmin, self.PsiUNorm.zmax)
        plt.gca().set_aspect('equal', adjustable='box')
        plt.xlabel('R')
        plt.ylabel('Z')
        plt.title('visualize gridue')

        k = [1, 2, 4, 3, 1]

        for i in range(len(self.rm)):
            for j in range(len(self.rm[0])):
                plt.plot(self.rm[i][j][k], self.zm[i][j][k])
                plt.pause(0.01)

    def get_config(self):
        """
        Returns a string indicating whether the
        """
        return self.config

    def get_func(self, _func):

            def make_sympy_func(var, expression):
                import sympy as sp
                _f = sp.lambdify(var, expression, 'numpy')
                return _f

            f_str_raw = _func

            f_str_raw = f_str_raw.replace(' ', '')
            delim = f_str_raw.index(',')

            var = f_str_raw[0: delim]
            expression = f_str_raw[delim + 1:]

            _func = make_sympy_func(var, expression)
            # TODO: Check Normalization of the function to 1
            return _func

    def CheckFunction(self, Str, Verbose=False):
        # can use a fancier test of tehe lambda function like in get_func above
        try:
            com = 'lambda {}:{}'.format(Str.split(',')[0], Str.split(',')[1])
            if Verbose: print(com)
            eval(com)
            ExpValid = True
        except:
            raise ValueError('Unable to parse function {} for entry {}. Lambda function expected:"x,f(x)"'.format(self.val, Name))
            ExpValid = False
        return ExpValid

    def GetFunctions(self, Patch, Verbose=False):

        poloidal_tag, radial_tag = Patch.get_tag()
        p_f = 'poloidal_f_' + poloidal_tag
        r_f = 'radial_f_' + radial_tag

        try:
            _poloidal_f = self.settings['grid_settings']['grid_generation'][p_f]
            valid_function = self.CheckFunction(_poloidal_f, Verbose)
            if valid_function:
                _poloidal_f = self.get_func(_poloidal_f)
            else:
                raise ValueError('# Invalid function entry. Applying default poloidal function.')
        except:
            _poloidal_f = self.settings['grid_settings']['grid_generation']['poloidal_f_default']
            valid_function = self.CheckFunction(_poloidal_f, Verbose)
            if valid_function:
                _poloidal_f = self.get_func(_poloidal_f)
            else:
                _poloidal_f = lambda x: x

        try:
            _radial_f = self.settings['grid_settings']['grid_generation'][r_f]
            valid_function = self.CheckFunction(_radial_f, Verbose)
            if valid_function:
                _radial_f = self.get_func(_radial_f)
            else:
                raise ValueError('# Invalid function entry. Applying default radial function.')
        except:
            _radial_f = self.settings['grid_settings']['grid_generation']['radial_f_default']
            valid_function = self.CheckFunction(_radial_f, Verbose)
            if valid_function:
                _radial_f = self.get_func(_radial_f)
            else:
                _radial_f = lambda x: x

        return (_radial_f, _poloidal_f)

    def GetNpoints(self, Patch):

        poloidal_tag, radial_tag = Patch.get_tag()
        np_tag = 'np_' + poloidal_tag
        nr_tag = 'nr_' + radial_tag
        try:
            np_cells = self.settings['grid_settings']['grid_generation'][np_tag]
        except:
            np_cells = self.settings['grid_settings']['grid_generation']['np_default']

        try:
            nr_cells = self.settings['grid_settings']['grid_generation'][nr_tag]
        except:
            nr_cells = self.settings['grid_settings']['grid_generation']['nr_default']

        return (nr_cells, np_cells)

    def GetCorrectDistortionSettings(self):
        if self.settings['grid_settings'].get('CorrectDistortion') is not None:
            CD = self.settings['grid_settings']['CorrectDistortion']
        else:
            CD = {}

        self.CorrectDistortion = CD

    def construct_grid(self, np_cells=1, nr_cells=1, Verbose=False, ShowVertices=False, RestartScratch=False, OptionTrace='theta', ExtraSettings={}, ListPatches='all'):

        # Straighten up East and West segments of our patches,
        # Plot borders and fill patches.
        if Verbose: print('Construct Grid')
        try:
            visual = self.settings['DEBUG']['visual']['subgrid']
        except:
            visual = False
        try:
            verbose = self.settings['DEBUG']['verbose']['grid_generation']
        except:
            verbose = False

        verbose = Verbose or verbose

        self.RefreshSettings()
        self.GetCorrectDistortionSettings()

        print('>>> Patches:', [k for k in self.patches.keys()])
        if RestartScratch:
            self.CurrentListPatch = {}

        for name, patch in self.patches.items():

            if self.CorrectDistortion.get(name) is not None:
               patch.CorrectDistortion = self.CorrectDistortion.get(name)
            elif self.CorrectDistortion.get(patch.get_tag()) is not None:
                patch.CorrectDistortion = self.CorrectDistortion.get(patch.get_tag())
            elif self.CorrectDistortion.get('all') is not None:
                patch.CorrectDistortion = self.CorrectDistortion.get('all')
            else:
                patch.CorrectDistortion = {'Active': False}
            if (ListPatches == 'all' and patch not in self.CurrentListPatch) or (ListPatches != 'all' and name in ListPatches):
                self.SetPatchBoundaryPoints(patch)
                (nr_cells, np_cells) = self.GetNpoints(patch)
                (_radial_f, _poloidal_f) = self.GetFunctions(patch)
                print('>>> Making subgrid in patch:{} with np={},nr={},fp={},fr={}'.format(name, np_cells, nr_cells, inspect.getsource(_poloidal_f), inspect.getsource(_radial_f)))
                patch.RemoveDuplicatePoints()
                patch.make_subgrid(self, np_cells, nr_cells, _poloidal_f=_poloidal_f, _radial_f=_radial_f, verbose=verbose, visual=visual, ShowVertices=ShowVertices)

                self.AdjustGrid(patch)
                self.CurrentListPatch[name] = patch

    def AdjustGrid(self, patch):

        # Adjust cell to any adjacent x-point
        self.AdjustPatch(patch)

        # Circular patch configuration requires adjustment of border to close loop.
        # Convention chosen: 'E' indicates closed loop

        try:
            if patch.TerminatesLoop:
                # Get patch name of adjacent patch for linking boundary points
                pname = self.PatchTagMap[self.ConnexionMap.get(patch.get_tag())['E'][0]]
                patch.AdjustBorder('E', self.patches[pname])
        except:
            pass

    def SetPatchBoundaryPoints(self, Patch):
        Patch.TerminatesLoop = False
        if self.ConnexionMap.get(Patch.get_tag()) is not None:
            if self.Verbose: print('Find connexion map for patch {}'.format(Patch.patchName))
            for v in self.ConnexionMap.get(Patch.get_tag()).items():
                Boundary, AdjacentPatch = v
                Patch.BoundaryPoints[Boundary] = self.GetBoundaryPoints(AdjacentPatch)
                if self.Verbose: print('Find Boundaries points for {}'.format(Patch.patchName))
            if self.ConnexionMap.get(Patch.get_tag()).get('E') is not None:
                Patch.TerminatesLoop = True

    def GetBoundaryPoints(self, AdjacentPatch):
        if AdjacentPatch is not None:
            PatchTag = AdjacentPatch[0]
            Boundary = AdjacentPatch[1]
            for patch in self.patches.values():
                if patch.get_tag() == PatchTag:
                   if Boundary == 'S':
                       return patch.S_vertices
                   elif Boundary == 'N':
                       return patch.N_vertices
                   elif Boundary == 'E':
                       return patch.E_vertices
                   elif Boundary == 'W':
                       return patch.W_vertices
        return None

    def CheckPatches(self, verbose=False):
        for name, patch in self.patches.items():
            if patch.platePatch:
                print(' # Checking patch: ', name)
                patch.CheckPatch(self)

    def add_guardc(self, cell_map, ixlb, ixrb, nxpt=1, eps=1e-3):

        def set_guard(cell_map, ix, iy, eps, boundary):
            # Note: 'USN' and 'right' is really just 'LSN' and 'left' settings.
            # TODO: Edit the code to reflect this at some point so the next reader is not overwhelmed.
            if boundary == 'left':
                ixn = ix + 1
                iyn = iy
                cell_map[ix][iy][1] = cell_map[ixn][iyn][1] + eps * (cell_map[ixn][iyn][1] - cell_map[ixn][iyn][2])
                cell_map[ix][iy][2] = cell_map[ixn][iyn][1]
                cell_map[ix][iy][3] = cell_map[ixn][iyn][3] + eps * (cell_map[ixn][iyn][3] - cell_map[ixn][iyn][4])
                cell_map[ix][iy][4] = cell_map[ixn][iyn][3]
                cell_map[ix][iy][0] = 0.25 * (cell_map[ix][iy][1] + cell_map[ix][iy][2] + cell_map[ix][iy][3] + cell_map[ix][iy][4])

            elif boundary == 'right':
                ixn = ix - 1
                iyn = iy
                cell_map[ix][iy][2] = cell_map[ixn][iyn][2] + eps * (cell_map[ixn][iyn][2] - cell_map[ixn][iyn][1])
                cell_map[ix][iy][1] = cell_map[ixn][iyn][2]
                cell_map[ix][iy][4] = cell_map[ixn][iyn][4] + eps * (cell_map[ixn][iyn][4] - cell_map[ixn][iyn][3])
                cell_map[ix][iy][3] = cell_map[ixn][iyn][4]
                cell_map[ix][iy][0] = 0.25 * (cell_map[ix][iy][1] + cell_map[ix][iy][2] + cell_map[ix][iy][3] + cell_map[ix][iy][4])

            elif boundary == 'bottom':
                ixn = ix
                iyn = iy + 1
                cell_map[ix][iy][1] = cell_map[ixn][iyn][1] + eps * (cell_map[ixn][iyn][1] - cell_map[ixn][iyn][3])
                cell_map[ix][iy][3] = cell_map[ixn][iyn][1]
                cell_map[ix][iy][2] = cell_map[ixn][iyn][2] + eps * (cell_map[ixn][iyn][2] - cell_map[ixn][iyn][4])
                cell_map[ix][iy][4] = cell_map[ixn][iyn][2]
                cell_map[ix][iy][0] = 0.25 * (cell_map[ix][iy][1] + cell_map[ix][iy][2] + cell_map[ix][iy][3] + cell_map[ix][iy][4])
            elif boundary == 'top':
                ixn = ix
                iyn = iy - 1
                cell_map[ix][iy][3] = cell_map[ixn][iyn][3] + eps * (cell_map[ixn][iyn][3] - cell_map[ixn][iyn][1])
                cell_map[ix][iy][1] = cell_map[ixn][iyn][3]
                cell_map[ix][iy][4] = cell_map[ixn][iyn][4] + eps * (cell_map[ixn][iyn][4] - cell_map[ixn][iyn][2])
                cell_map[ix][iy][2] = cell_map[ixn][iyn][4]
                cell_map[ix][iy][0] = 0.25 * (cell_map[ix][iy][1] + cell_map[ix][iy][2] + cell_map[ix][iy][3] + cell_map[ix][iy][4])

            return cell_map

        np = len(cell_map) - 2
        nr = len(cell_map[0]) - 2

        for iy in range(1, nr + 1):
            ix = ixlb
            cell_map = set_guard(cell_map, ix, iy, eps, boundary='left')
            ix = ixrb + 1
            cell_map = set_guard(cell_map, ix, iy, eps, boundary='right')

        for ix in range(np + 2):
            iy = 0
            cell_map = set_guard(cell_map, ix, iy, eps, boundary='bottom')
            iy = nr + 1
            cell_map = set_guard(cell_map, ix, iy, eps, boundary='top')

        return cell_map

    def SetupPatchMatrix(self):
        p = self.patches

        if self.config in ['LSN', 'USN']:
            self.patch_matrix = [
            [[None],   [None],   [None],   [None],   [None],   [None],   [None], [None]],
            [[None], p['IDL'], p['ISB'], p['IST'], p['OST'], p['OSB'], p['ODL'], [None]],
            [[None], p['IPF'], p['ICB'], p['ICT'], p['OCT'], p['OCB'], p['OPF'], [None]],
            [[None],   [None],   [None],   [None],   [None],   [None],   [None], [None]]
            ]

        elif self.config in ['SF45', 'SF75', 'SF105', 'SF135']:
            self.patch_matrix = [
            [[None], [None],  [None],  [None],  [None],  [None],  [None],  [None], [None], [None],  [None],  [None], [None]],
            [[None], p['A3'], p['B3'], p['C3'], p['D3'], p['E3'], p['F3'], p['G3'], [None], [None], p['H3'], p['I3'], [None]],
            [[None], p['A2'], p['B2'], p['C2'], p['D2'], p['E2'], p['F2'], p['G2'], [None], [None], p['H2'], p['I2'], [None]],
            [[None], p['A1'], p['B1'], p['C1'], p['D1'], p['E1'], p['F1'], p['G1'], [None], [None], p['H1'], p['I1'], [None]],
            [[None], [None],  [None],  [None],  [None],  [None],  [None],  [None], [None], [None],  [None],  [None], [None]]
            ]
        elif self.config in ['SF15', 'SF165']:
            self.patch_matrix = [
            [[None], [None],  [None],  [None],  [None],  [None],  [None],  [None], [None], [None],  [None], [None],  [None]],
            [[None], p['A3'], p['B3'], p['C3'], p['D3'], p['E3'], p['F3'], [None], [None], p['G3'], p['H3'], p['I3'], [None]],
            [[None], p['A2'], p['B2'], p['C2'], p['D2'], p['E2'], p['F2'], [None], [None], p['G2'], p['H2'], p['I2'], [None]],
            [[None], p['A1'], p['B1'], p['C1'], p['D1'], p['E1'], p['F1'], [None], [None], p['G1'], p['H1'], p['I1'], [None]],
            [[None], [None],  [None],  [None],  [None],  [None],  [None],  [None], [None], [None],  [None],  [None], [None]]
            ]

        elif self.config in ['UDN']:
            self.patch_matrix = [
            [[None],  [None],  [None],  [None],  [None], [None], [None], [None], [None], [None], [None], [None]],
            [[None], p['A3'], p['B3'], p['C3'], p['D3'], [None], [None], p['E3'], p['F3'], p['G3'], p['H3'], [None]],
            [[None], p['A2'], p['B2'], p['C2'], p['D2'], [None], [None], p['E2'], p['F2'], p['G2'], p['H2'], [None]],
            [[None], p['A1'], p['B1'], p['C1'], p['D1'], [None], [None], p['E1'], p['F1'], p['G1'], p['H1'], [None]],
            [[None],  [None],  [None],  [None],  [None], [None], [None], [None], [None], [None], [None], [None]]
            ]

    def concat_grid(self):

        patch_matrix = self.patch_matrix

        for patch in self.patches.values():
            patch.npol = len(patch.cell_grid[0]) + 1
            patch.nrad = len(patch.cell_grid) + 1

        if self.parent.settings['grid_settings']['num_xpt'] == 1:

            np_total = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][1:-1]])) + 2
            nr_total = int(np.sum([patch[1].nrad - 1 for patch in patch_matrix[1:3]])) + 2

            rm = np.zeros((np_total, nr_total, 5), order='F')
            zm = np.zeros((np_total, nr_total, 5), order='F')

            ixcell = 0
            jycell = 0

            # Iterate over all the patches in our SNL configuration (we exclude guard cells denoted by '[None]')
            for ixp in range(1, 7):

                nr_sum = 0
                for jyp in range(1, 3):
                    # Point to the current patch we are operating on.
                    local_patch = patch_matrix[jyp][ixp]
                    nr_sum += local_patch.nrad - 1

                    # Access the grid that is contained within this local_patch.
                    # ixl - number of poloidal cells in the patch.
                    for ixl in range(len(local_patch.cell_grid[0])):
                        # jyl - number of radial cells in the patch
                        for jyl in range(len(local_patch.cell_grid)):

                            ixcell = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][1:ixp + 1]])) \
                                    - len(local_patch.cell_grid[0]) + ixl + 1

                            jycell = nr_sum - (local_patch.nrad - 1) + jyl + 1

                            ind = 0
                            for coor in ['CENTER', 'SW', 'SE', 'NW', 'NE']:
                                rm[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].x
                                zm[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].y
                                ind += 1

            # Flip indices into gridue format.
            for i in range(len(rm)):
                rm[i] = rm[i][::-1]
            for i in range(len(zm)):
                zm[i] = zm[i][::-1]

            # Add guard cells to the concatenated grid.
            ixrb = len(rm) - 2
            ixlb = 0
            self.rm = self.add_guardc(rm, ixlb, ixrb)
            self.zm = self.add_guardc(zm, ixlb, ixrb)

            try:
                debug = self.settings['DEBUG']['visual']['gridue']
            except:
                debug = False

            if debug:
                self.animate_grid()

        elif self.parent.settings['grid_settings']['num_xpt'] == 2:

            if self.config in ['SF45', 'SF75', 'SF105', 'SF135']:
                pindex1 = 8
                pindex2 = 10
                pindex3 = 12
            elif self.config in ['SF15', 'SF165']:
                pindex1 = 7
                pindex2 = 9
                pindex3 = 12
            elif self.config in ['UDN']:
                pindex1 = 5
                pindex2 = 7
                pindex3 = 11

            # Total number of poloidal indices in all subgrids.
            np_total1 = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][1:pindex1]])) + 2

            # Total number of radial indices in all subgrids.
            nr_total1 = int(np.sum([patch[1].nrad - 1 for patch in patch_matrix[1:4]])) + 2

            # Total number of poloidal indices in all subgrids.
            np_total2 = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][pindex2:pindex3]])) + 2

            # Total number of radial indices in all subgrids.
            nr_total2 = int(np.sum([patch[pindex2].nrad - 1 for patch in patch_matrix[1:4]])) + 2

            rm1 = np.zeros((np_total1, nr_total1, 5), order='F')
            zm1  = np.zeros((np_total1, nr_total1, 5), order='F')
            rm2 = np.zeros((np_total2, nr_total2, 5), order='F')
            zm2  = np.zeros((np_total2, nr_total2, 5), order='F')

            ixcell = 0
            jycell = 0

            # Iterate over all the patches in our DNL configuration (we exclude guard cells denoted by '[None]')
            for ixp in range(1, pindex1):

                nr_sum = 0
                for jyp in range(1, 4):
                    # Point to the current patch we are operating on.
                    local_patch = patch_matrix[jyp][ixp]

                    if local_patch == [None]:
                        continue

                    nr_sum += local_patch.nrad - 1

                    # Access the grid that is contained within this local_patch.
                    # ixl - number of poloidal cells in the patch.
                    for ixl in range(len(local_patch.cell_grid[0])):
                        # jyl - number of radial cells in the patch
                        for jyl in range(len(local_patch.cell_grid)):

                            ixcell = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][1:ixp + 1]])) \
                                    - len(local_patch.cell_grid[0]) + ixl + 1

                            jycell = nr_sum - (local_patch.nrad - 1) + jyl + 1

                            ind = 0
                            for coor in ['CENTER', 'SW', 'SE', 'NW', 'NE']:
                                rm1[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].x
                                zm1[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].y
                                ind += 1

            ixcell = 0
            jycell = 0

            for ixp in range(pindex2, pindex3):

                nr_sum = 0
                for jyp in range(1, 4):
                    # Point to the current patch we are operating on.
                    local_patch = patch_matrix[jyp][ixp]

                    if local_patch == [None]:
                        continue

                    nr_sum += local_patch.nrad - 1

                    # Access the grid that is contained within this local_patch.
                    # ixl - number of poloidal cells in the patch.
                    for ixl in range(len(local_patch.cell_grid[0])):
                        # jyl - number of radial cells in the patch
                        for jyl in range(len(local_patch.cell_grid)):

                            ixcell = int(np.sum([patch.npol - 1 for patch in patch_matrix[1][pindex2:ixp + 1]])) \
                                    - len(local_patch.cell_grid[0]) + ixl + 1

                            jycell = nr_sum - (local_patch.nrad - 1) + jyl + 1

                            ind = 0
                            for coor in ['CENTER', 'SW', 'SE', 'NW', 'NE']:
                                rm2[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].x
                                zm2[ixcell][jycell][ind] = local_patch.cell_grid[jyl][ixl].vertices[coor].y
                                ind += 1

            # Flip indices into gridue format.
            for i in range(len(rm1)):
                rm1[i] = rm1[i][::-1]
            for i in range(len(zm1)):
                zm1[i] = zm1[i][::-1]
            for i in range(len(rm2)):
                rm2[i] = rm2[i][::-1]
            for i in range(len(zm2)):
                zm2[i] = zm2[i][::-1]

            # Add guard cells to the concatenated grid.
            ixrb1 = len(rm1) - 2
            ixlb1 = 0
            ixrb2 = len(rm2) - 2
            ixlb2 = 0

            rm1 = self.add_guardc(rm1, ixlb1, ixrb1)
            zm1 = self.add_guardc(zm1, ixlb1, ixrb1)
            rm2 = self.add_guardc(rm2, ixlb2, ixrb2)
            zm2 = self.add_guardc(zm2, ixlb2, ixrb2)

            self.rm = np.concatenate((rm1, rm2))
            self.zm = np.concatenate((zm1, zm2))

            try:
                debug = self.yaml['DEBUG']['visual']['gridue']
            except:
                debug = False

            if debug:
                self.animate_grid()
