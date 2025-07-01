from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="memory_manager",
    version="1.0.0",
    author="AI Code Specialist",
    author_email="ai@example.com",
    description="Enterprise-grade memory management system for Python web applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/memory_manager",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
    ],
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "PyYAML>=6.0",
    ],
    extras_require={
        "full": [
            "pympler>=1.0.1",
            "objgraph>=3.5.0",
            "prometheus-client>=0.14.1",
            "memory-profiler>=0.60.0",
        ],
        "flask": [
            "flask>=2.0.0",
        ],
        "fastapi": [
            "fastapi>=0.68.0",
            "pydantic>=1.9.0",
            "uvicorn>=0.15.0",
        ],
    }
) 