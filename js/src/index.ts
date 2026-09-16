import { DatabaseEngineItem } from '@sonolus/core'

export { susToLevelData } from './sus/convert.js'

export const version = '0.0.0'

export const databaseEngineItem = {
    name: 'next-sekai',
    version: 13,
    title: {
        en: 'Next SEKAI',
    },
    subtitle: {
        en: 'Next SEKAI',
    },
    author: {
        en: 'qwewqa#590353',
    },
    description: {
        en: [
            'A new Project Sekai inspired engine for Sonolus.',
            `Version: ${version}`,
            '',
            'GitHub Repository',
            'https://github.com/Next-SEKAI/sonolus-next-sekai-engine',
        ].join('\n'),
    },
} as const satisfies Partial<DatabaseEngineItem>
