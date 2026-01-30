#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
古文卡片学习软件安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="ancient-chinese-cards",
    version="1.0.0",
    description="一款专为古文学习设计的卡片管理工具",
    long_description="""
古文卡片学习软件是一款专为学习古文的学生、教师、学者和古文爱好者设计的卡片管理工具。
它可以帮助用户制作、管理和搜索古文学习卡片，提高学习效率和体验。

主要功能：
1. 卡片制作：创建包含关键词、释义、出处、原文引用和注释的古文卡片
2. 卡片管理：按字母顺序自动排序并生成概览视图
3. 内容搜索：支持全文搜索卡片内容，快速定位所需信息
4. 导入导出：支持按特定格式导入导出卡片数据，方便分享和备份
5. 古文注释系统：支持添加注音、释义、出处等多层次注释
""",
    author="古文卡片学习软件团队",
    author_email="jumaozhixing@outlook.com",
    url="https://github.com/ancient-chinese-cards/ancient-chinese-cards",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['data/*.json'],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "Topic :: Text Processing :: General",
    ],
    keywords="ancient chinese, learning, flashcards, education",
    python_requires='>=3.6',
    install_requires=[
        'pypinyin>=0.40.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.10',
            'flake8>=3.8',
        ],
    },
    entry_points={
        'console_scripts': [
            'ancient-chinese-cards=ancient_chinese_cards.main:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/ancient-chinese-cards/ancient-chinese-cards/issues',
        'Source': 'https://github.com/ancient-chinese-cards/ancient-chinese-cards',
    },
)