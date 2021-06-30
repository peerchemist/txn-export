from setuptools import setup

setup(name='txn_history',
      version='0.1',
      description='Export Peercoin transaction history to Excel format.',
      keywords=["blockchain", "peercoin"],
      url='',
      author='Peerchemist',
      author_email='peerchemist@protonmail.ch',
      license='BSD',
      packages=['txn-history'],
      python_requires='>3.7',
      install_requires=['requests', 'xlsxwriter', 'tkinter']
      )
