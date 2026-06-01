"use client"

import { Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { GenerateForm } from "@/components/create/GenerateForm"
import { TaskView } from "@/components/create/TaskView"

function CreateContent() {
  const searchParams = useSearchParams()
  const taskId = searchParams.get("task")

  if (taskId) {
    return <TaskView taskId={taskId} />
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <GenerateForm />
    </div>
  )
}

export default function CreatePage() {
  return (
    <Suspense fallback={null}>
      <CreateContent />
    </Suspense>
  )
}
