import { cp, mkdir, rm } from "node:fs/promises"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(here, "..")
const projectRoot = resolve(frontendRoot, "..")
const source = resolve(frontendRoot, "out")
const target = resolve(projectRoot, "src", "api", "static_frontend")

await rm(target, { recursive: true, force: true })
await mkdir(target, { recursive: true })
await cp(source, target, { recursive: true })

console.log(`Copied static frontend to ${target}`)
