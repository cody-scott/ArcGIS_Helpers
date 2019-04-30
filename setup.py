from setuptools import setup

setup(name='arcgis_helpers',
      version='0.9.3',
      description='Helpers for ArcGIS.',
      url='',
      author='Cody',
      author_email='',
      license='MIT',
      packages=['arcgis_helpers'],
      # package_dir={'arcgis_helpers': 'arcgis_helpers', 'arc_np': 'arc_np'},
      # package_data={'arcgis_helpers': ['esri/toolboxes/*.*']},
      install_requires=[
          'pyperclip',
      ],
      zip_safe=False)
