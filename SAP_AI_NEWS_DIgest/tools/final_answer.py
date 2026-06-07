from smolagents.tools import Tool


class FinalAnswerTool(Tool):
    name = "final_answer"
    description = "Provides a final answer to the given problem."
    inputs = {
        "answer": {
            "type": "string",
            "description": "The final answer to the problem"
        }
    }
    output_type = "string"

    def forward(self, answer: str) -> str:
        return answer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_initialized = False
