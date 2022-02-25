from os import path

from setuptools import setup

readme_file_path = path.join(path.abspath(path.dirname(__file__)), 'README.md')
with open(readme_file_path, encoding='utf-8') as readme_file:
    long_description = readme_file.read()

setup(
    name='botox-di',
    version='1.5.2',
    url='https://github.com/lebedec/botox-di',
    project_urls={
        'Code': 'https://github.com/lebedec/botox-di',
        'Issue tracker': 'https://github.com/lebedec/botox-di/issues'
    },
    description='Botox is a dependency injection implementation based on Python type annotations.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Ilya Lebedev',
    author_email='lebedev.games.mail@gmail.com',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
    ],
    packages=['botox'],
    platforms='any',
    python_requires='>=3.6'
)
